import os
import cv2
import supervisely as sly
from typing import List, Dict, Tuple
import pycocotools.mask as mask_util
import numpy as np
from copy import deepcopy


def coco_to_sly_ann(
    meta: sly.ProjectMeta,
    coco_categories: List[dict],
    coco_ann: List[Dict],
    image_size: Tuple[int, int],
    ignore_bbox: bool = False,
) -> sly.Annotation:
    """Convert COCO annotation to Supervisely annotation.

    :param meta: ProjectMeta of Supervisely project.
    :type meta: sly.ProjectMeta
    :param coco_categories: List of COCO categories.
    :type coco_categories: List[dict]
    :param coco_ann: List of COCO annotations.
    :type coco_ann: List[Dict]
    :param image_size: size of image.
    :type image_size: Tuple[int, int]
    :param ignore_bbox: if True, bounding boxes will be ignored, defaults to False
    :type ignore_bbox: bool, optional
    :return: Supervisely annotation.
    :rtype: sly.Annotation
    """

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

        if not ignore_bbox:
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


def convert_rle_mask_to_polygon(coco_ann: List[Dict]) -> List[sly.Polygon]:
    """Convert RLE mask to List of Supervisely Polygons.

    :param coco_ann: List of COCO annotations.
    :type coco_ann: List[Dict]
    :return: List of Supervisely Polygons.
    :rtype: List[sly.Polygon]
    """
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


def convert_polygon_vertices(
    coco_ann: List[Dict], image_size: Tuple[int, int]
) -> List[sly.Polygon]:
    """Convert polygon vertices to Supervisely Polygons.

    :param coco_ann: List of COCO annotations.
    :type coco_ann: List[Dict]
    :param image_size: size of image.
    :type image_size: Tuple[int, int]
    :return: List of Supervisely Polygons.
    :rtype: List[sly.Polygon]
    """
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

            if all(results):
                interiors[idx].append(deepcopy(exteriors[idy]))
                id2del.append(idy)

    for j in sorted(id2del, reverse=True):
        del exteriors[j]

    figures = []
    for exterior, interior in zip(exteriors, interiors.values()):
        exterior = [sly.PointLocation(y, x) for x, y in exterior]
        interior = [[sly.PointLocation(y, x) for x, y in points] for points in interior]
        figures.append(sly.Polygon(exterior, interior))

    return figures


def coco_category_to_class_name(coco_categories: List[dict]) -> Dict:
    """Create dictionary with COCO category id as key and category name as value.

    :param coco_categories: List of COCO categories.
    :type coco_categories: List[dict]
    :return: Dictionary with COCO category id as key and category name as value.
    :rtype: Dict
    """
    return {category["id"]: category["name"] for category in coco_categories}
