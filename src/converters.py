import os
import shutil
import cv2
import supervisely as sly
from pycocotools.coco import COCO
import pycocotools.mask as mask_util
import numpy as np
from copy import deepcopy


def coco_to_supervisely(src_path: str, dst_path: str):
    META = sly.ProjectMeta()

    dataset_names = sly.fs.get_subdirs(src_path)
    dataset_paths = [os.path.join(src_path, name) for name in dataset_names]

    for dataset_name, dataset_path in zip(dataset_names, dataset_paths):
        coco_ann_dir = os.path.join(dataset_path, "annotations")
        coco_ann_path = os.path.join(coco_ann_dir, "instances.json")
        if coco_ann_path is not None:
            try:
                coco_instances = COCO(annotation_file=coco_ann_path)
            except Exception as e:
                sly.logger.warning(
                    f"File {coco_ann_path} has been skipped due to error: {e}"
                )
                continue

            categories = coco_instances.loadCats(ids=coco_instances.getCatIds())
            coco_images = coco_instances.imgs
            coco_anns = coco_instances.imgToAnns

            sly_dataset_dir = create_sly_dataset_dir(
                dst_path, dataset_name=dataset_name
            )
            img_dir = os.path.join(sly_dataset_dir, "img")
            ann_dir = os.path.join(sly_dataset_dir, "ann")
            META = get_sly_meta_from_coco(META, dst_path, categories, dataset_name)

            for img_id, img_info in coco_images.items():
                image_name = img_info["file_name"]
                if "/" in image_name:
                    image_name = os.path.basename(image_name)
                if sly.fs.file_exists(os.path.join(dataset_path, "images", image_name)):
                    img_ann = coco_anns[img_id]
                    img_size = (img_info["height"], img_info["width"])
                    ann = create_sly_ann_from_coco_annotation(
                        meta=META,
                        coco_categories=categories,
                        coco_ann=img_ann,
                        image_size=img_size,
                    )
                    move_trainvalds_to_sly_dataset(
                        dataset_dir=dataset_path,
                        coco_image=img_info,
                        ann=ann,
                        img_dir=img_dir,
                        ann_dir=ann_dir,
                    )

    sly.logger.info(f"COCO dataset converted to Supervisely project: {dst_path}")
    return dst_path


def create_sly_dataset_dir(dst_path, dataset_name):
    dataset_dir = os.path.join(dst_path, dataset_name)
    sly.fs.mkdir(dataset_dir)
    img_dir = os.path.join(dataset_dir, "img")
    sly.fs.mkdir(img_dir)
    ann_dir = os.path.join(dataset_dir, "ann")
    sly.fs.mkdir(ann_dir)
    return dataset_dir


def get_sly_meta_from_coco(meta, dst_path, coco_categories, dataset_name):
    path_to_meta = os.path.join(dst_path, "meta.json")
    if not os.path.exists(path_to_meta):
        meta = dump_meta(meta, coco_categories, path_to_meta)
    elif dataset_name not in ["train2014", "val2014", "train2017", "val2017"]:
        meta = dump_meta(meta, coco_categories, path_to_meta)
    return meta


def dump_meta(meta, coco_categories, path_to_meta):
    meta = create_sly_meta_from_coco_categories(meta, coco_categories)
    meta_json = meta.to_json()
    sly.json.dump_json_file(meta_json, path_to_meta)
    return meta


def create_sly_meta_from_coco_categories(meta, coco_categories):
    colors = []
    for category in coco_categories:
        if category["name"] in [obj_class.name for obj_class in meta.obj_classes]:
            continue
        new_color = sly.color.generate_rgb(colors)
        colors.append(new_color)
        obj_class = sly.ObjClass(category["name"], sly.AnyGeometry, new_color)
        meta = meta.add_obj_class(obj_class)
    return meta


def create_sly_ann_from_coco_annotation(meta, coco_categories, coco_ann, image_size):
    labels = []
    imag_tags = []
    name_cat_id_map = coco_category_to_class_name(coco_categories)
    for object in coco_ann:
        curr_labels = []

        segm = object.get("segmentation")
        if segm is not None and len(segm) > 0:
            obj_class_name = name_cat_id_map[object["category_id"]]
            obj_class = meta.get_obj_class(obj_class_name)
            if type(segm) is dict:
                polygons = convert_rle_mask_to_polygon(object)
                for polygon in polygons:
                    figure = polygon
                    label = sly.Label(figure, obj_class)
                    labels.append(label)
            elif type(segm) is list and object["segmentation"]:
                figures = convert_polygon_vertices(object, image_size)
                curr_labels.extend([sly.Label(figure, obj_class) for figure in figures])
        labels.extend(curr_labels)

        bbox = object.get("bbox")
        if bbox is not None and len(bbox) == 4:
            obj_class_name = name_cat_id_map[object["category_id"]]
            obj_class = meta.get_obj_class(obj_class_name)
            if len(curr_labels) > 1:
                for label in curr_labels:
                    bbox = label.geometry.to_bbox()
                    labels.append(sly.Label(bbox, obj_class))
            else:
                x, y, w, h = bbox
                rectangle = sly.Label(sly.Rectangle(y, x, y + h, x + w), obj_class)
                labels.append(rectangle)

        caption = object.get("caption")
        if caption is not None:
            imag_tags.append(sly.Tag(meta.get_tag_meta("caption"), caption))

    return sly.Annotation(image_size, labels=labels, img_tags=imag_tags)


def convert_rle_mask_to_polygon(coco_ann):
    if type(coco_ann["segmentation"]["counts"]) is str:
        coco_ann["segmentation"]["counts"] = bytes(
            coco_ann["segmentation"]["counts"], encoding="utf-8"
        )
        mask = mask_util.decode(coco_ann["segmentation"])
    else:
        rle_obj = mask_util.frPyObjects(
            coco_ann["segmentation"],
            coco_ann["segmentation"]["size"][0],
            coco_ann["segmentation"]["size"][1],
        )
        mask = mask_util.decode(rle_obj)
    mask = np.array(mask, dtype=bool)
    return sly.Bitmap(mask).to_contours()


def convert_polygon_vertices(coco_ann, image_size):
    polygons = coco_ann["segmentation"]
    if all(type(coord) is float for coord in polygons):
        polygons = [polygons]

    exteriors = []
    for polygon in polygons:
        polygon = [
            polygon[i * 2 : (i + 1) * 2] for i in range((len(polygon) + 2 - 1) // 2)
        ]
        exteriors.append([(width, height) for width, height in polygon])

    interiors = {idx: [] for idx in range(len(exteriors))}
    id2del = []
    for idx, exterior in enumerate(exteriors):
        temp_img = np.zeros(image_size + (3,), dtype=np.uint8)
        geom = sly.Polygon([sly.PointLocation(y, x) for x, y in exterior])
        geom.draw_contour(temp_img, color=[255, 255, 255])
        im = cv2.cvtColor(temp_img, cv2.COLOR_RGB2GRAY)
        contours, _ = cv2.findContours(im, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        if len(contours) == 0:
            continue
        for idy, exterior2 in enumerate(exteriors):
            if idx == idy or idy in id2del:
                continue
            results = [
                cv2.pointPolygonTest(contours[0], (x, y), False) > 0
                for x, y in exterior2
            ]
            # if results of True, then all points are inside or on contour
            if all(results):
                interiors[idx].append(deepcopy(exteriors[idy]))
                id2del.append(idy)

    # remove contours from exteriors that are inside other contours
    for j in sorted(id2del, reverse=True):
        del exteriors[j]

    figures = []
    for exterior, interior in zip(exteriors, interiors.values()):
        exterior = [sly.PointLocation(y, x) for x, y in exterior]
        interior = [[sly.PointLocation(y, x) for x, y in points] for points in interior]
        figures.append(sly.Polygon(exterior, interior))

    return figures


def move_trainvalds_to_sly_dataset(dataset_dir, coco_image, ann, img_dir, ann_dir):
    image_name = coco_image["file_name"]
    if "/" in image_name:
        image_name = os.path.basename(image_name)
    ann_json = ann.to_json()
    coco_img_path = os.path.join(dataset_dir, "images", image_name)
    sly_img_path = os.path.join(img_dir, image_name)
    if sly.fs.file_exists(os.path.join(coco_img_path)):
        sly.json.dump_json_file(ann_json, os.path.join(ann_dir, f"{image_name}.json"))
        shutil.copy(coco_img_path, sly_img_path)


def coco_category_to_class_name(coco_categories):
    return {category["id"]: category["name"] for category in coco_categories}
