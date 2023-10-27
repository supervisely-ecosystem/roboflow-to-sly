import os
import shutil
import supervisely as sly
from time import sleep
from datetime import datetime

import roboflow
from supervisely.app.widgets import (
    Container,
    Card,
    Table,
    Button,
    Progress,
    Text,
    Flexbox,
)
import src.globals as g
from src.roboflow_api import download_project
from src.converters import coco_to_supervisely


COLUMNS = [
    "COPYING STATUS",
    "ID",
    "NAME",
    "CREATED",
    "UPDATED",
    "ROBOFLOW URL",
    "SUPERVISELY URL",
]

projects_table = Table(fixed_cols=3, per_page=20, sort_column_id=1)
projects_table.hide()

copy_button = Button("Copy", icon="zmdi zmdi-copy")
stop_button = Button("Stop", icon="zmdi zmdi-stop", button_type="danger")
stop_button.hide()

buttons_flexbox = Flexbox([copy_button, stop_button])

copying_progress = Progress()
good_results = Text(status="success")
bad_results = Text(status="error")
good_results.hide()
bad_results.hide()

card = Card(
    title="3️⃣ Copying",
    description="Copy selected projects from Roboflow to Supervisely.",
    content=Container(
        [projects_table, buttons_flexbox, copying_progress, good_results, bad_results]
    ),
    collapsable=True,
)
card.lock()
card.collapse()


def build_projects_table() -> None:
    """Fills the table with projects from Roboflow API.
    Uses global g.STATE.selected_projects to get the list of projects to show.
    """
    sly.logger.debug("Building projects table...")
    projects_table.loading = True
    rows = []

    for project in g.STATE.selected_projects:
        project_url = g.DEFAULT_APP_ADDRESS + f"/{project.id}"

        rows.append(
            [
                g.COPYING_STATUS.waiting,
                project.id,
                project.name,
                datetime_to_str(project.created),
                datetime_to_str(project.updated),
                f'<a href="{project_url}" target="_blank">{project_url}</a>',
                "",
            ]
        )

    sly.logger.debug(f"Prepared {len(rows)} rows for the projects table.")

    projects_table.read_json(
        {
            "columns": COLUMNS,
            "data": rows,
        }
    )

    projects_table.loading = False
    projects_table.show()

    sly.logger.debug("Projects table is built.")


def datetime_to_str(datetime_object: datetime) -> str:
    """Converts datetime object to string for HTML table.

    :param datetime_object: datetime object
    :type datetime_object: datetime
    :return: HTML-formatted string
    :rtype: str
    """
    return datetime_object.strftime("<b>%Y-%m-%d</b> %H:%M:%S")


@copy_button.click
def start_copying() -> None:
    """Main function for copying projects from Roboflow to Supervisely.

    1. Tries to download the project from Roboflow API and save it to the zip archive.
    2. Unpacks the project archive, converts it to Supervisely format and uploads it to Supervisely.
    3. Updates cells in the projects table by project ID.
    4. Clears the download and upload directories.
    5. Stops the application.
    """
    sly.logger.debug(
        f"Copying button is clicked. Selected projects: {g.STATE.selected_projects}"
    )

    stop_button.show()
    copy_button.text = "Copying..."
    g.STATE.continue_copying = True

    def save_project_to_zip(
        project: roboflow.Project, archive_path: str, retry: int = 0
    ) -> bool:
        """Tries to download the project from Roboflow API and save it to the zip archive.
        Functions tries to download the task data 10 times if the archive is empty and
        returns False if it can't download the data after 10 retries. Otherwise returns True.

        :param project: project object from Roboflow API
        :type task_id: roboflow.Project
        :param archive_path: path to the zip archive on the local machine
        :type archive_path: str
        :param retry: current number of retries, defaults to 0
        :type retry: int, optional
        :return: download status (True if the archive is not empty, False otherwise)
        :rtype: bool
        """
        sly.logger.debug(
            f"Trying to retreive project {project.name} archive from Roboflow API..."
        )
        download_status = download_project(project, archive_path)

        if not download_status:
            sly.logger.info(
                f"Will retry to download project {project.name}, because download was unsuccessful."
            )
            if retry < 10:
                # Try to download the task data again.
                retry += 1
                timer = 5
                while timer > 0:
                    sly.logger.info(f"Retry {retry} in {timer} seconds...")
                    sleep(1)
                    timer -= 1

                sly.logger.info(f"Retry {retry} to download project {project.name}...")
                save_project_to_zip(project, archive_path, retry)
            else:
                # If the archive is empty after 10 retries, return False.
                sly.logger.error(
                    f"Can't download project {project.name} after 10 retries."
                )
                return False
        else:
            sly.logger.debug(
                f"Archive for project {project.name} was downloaded successfully."
            )
            return True

    succesfully_uploaded = 0
    uploaded_with_errors = 0

    with copying_progress(
        total=len(g.STATE.selected_projects), message="Copying..."
    ) as pbar:
        for project in g.STATE.selected_projects:
            if not g.STATE.continue_copying:
                sly.logger.info("Stop button pressed. Will stop copying.")
                break
            sly.logger.debug(f"Copying project {project.name}")
            update_cells(project.id, new_status=g.COPYING_STATUS.working)

            archive_path = os.path.join(g.ARCHIVE_DIR, f"{project.name}.zip")
            download_status = save_project_to_zip(project, archive_path)

            if not download_status:
                sly.logger.warning(f"Project {project.name} was not downloaded.")
                update_cells(project.id, new_status=g.COPYING_STATUS.error)
                uploaded_with_errors += 1
                continue

            sly.logger.info(f"Project {project.name} was downloaded successfully.")

            upload_status = convert_and_upload(project, archive_path)

            if upload_status:
                sly.logger.info(f"Project {project.name} was uploaded successfully.")
                new_status = g.COPYING_STATUS.copied
                succesfully_uploaded += 1
            else:
                sly.logger.warning(f"Project {project.name} was not uploaded.")
                new_status = g.COPYING_STATUS.error
                uploaded_with_errors += 1

            update_cells(project.id, new_status=new_status)
            sly.logger.debug(f"Updated project {project.name} in the projects table.")

            sly.logger.info(f"Finished processing project {project.name}.")

            pbar.update(1)

    if succesfully_uploaded:
        good_results.text = f"Succesfully uploaded {succesfully_uploaded} projects."
        good_results.show()
    if uploaded_with_errors:
        bad_results.text = f"Uploaded {uploaded_with_errors} projects with errors."
        bad_results.show()

    copy_button.text = "Copy"
    stop_button.hide()

    sly.logger.info(f"Finished copying {len(g.STATE.selected_projects)} projects.")

    if sly.is_development():
        # * For debug purposes it's better to save the data from Roboflow API.
        sly.logger.debug(
            "Development mode, will not stop the application. "
            "And NOT clean download and upload directories."
        )
        return

    sly.fs.clean_dir(g.ARCHIVE_DIR)
    sly.fs.clean_dir(g.UNPACKED_DIR)

    sly.logger.info(
        f"Removed content from {g.ARCHIVE_DIR} and {g.UNPACKED_DIR}."
        "Will stop the application."
    )

    from migration_tool.src.main import app

    app.stop()


def convert_and_upload(project: roboflow.Project, archive_path: str) -> bool:
    """Unpacks the project archive, converts it to Supervisely format and uploads it to Supervisely.

    :param project: project object from Roboflow API
    :type project: roboflow.Project
    :param archive_path: path to the project archive on the local machine
    :type archive_path: str
    :return: status of the upload (True if the upload was successful, False otherwise)
    :rtype: bool
    """
    sly.logger.debug(f"Converting and uploading project {project.name}...")
    extract_path = os.path.join(g.UNPACKED_DIR, project.name)

    sly.fs.unpack_archive(archive_path, extract_path, remove_junk=True)
    sly.logger.debug(f"Unpacked {archive_path} to {extract_path}")

    prepare_coco(extract_path)
    converted_path = os.path.join(g.CONVERTED_DIR, project.name)

    try:
        coco_to_supervisely(extract_path, converted_path)
    except Exception as e:
        sly.logger.warning(f"Can't convert project {project.name}: {e}")
        return False

    sly.logger.debug(f"Converted {extract_path} to {converted_path}")

    try:
        (sly_id, sly_name) = sly.Project.upload(
            converted_path,
            g.api,
            g.STATE.selected_workspace,
            project.name,
        )
    except Exception as e:
        sly.logger.warning(f"Can't upload project {project.name} to Supervisely: {e}")
        return False

    project_info = g.api.project.get_info_by_id(sly_id)

    try:
        new_url = sly.utils.abs_url(project_info.url)
    except Exception:
        new_url = project_info.url
    sly.logger.debug(f"New URL for images project: {new_url}")
    update_cells(project.id, new_url=new_url)

    return True


def prepare_coco(directory: str) -> None:
    """Prepares correct structure of COCO format from Roboflow to Supervisely.

    1. Remove all files in directory (left only subdirectories)
    2. For each subdirectory (which will be a dataset):
        2.1. Create annotations directory
        2.2. Move _annotations.coco.json from subdirectory to annotations directory
        2.3. Rename _annotations.coco.json in annotations directory to instances.json
        2.4. Create images directory
        2.5. Move all images from subdirectory to images directory

    :param directory: path to the directory with COCO structure
    :type directory: str
    """
    sly.logger.debug(f"Preparing COCO structure in {directory}")

    root_files = sly.fs.list_files(directory)
    for root_file in root_files:
        if not os.path.isdir(root_file):
            sly.fs.silent_remove(root_file)
            sly.logger.debug(f"Removed file {root_file} from {directory}")

    subdirectories = [
        os.path.join(directory, name) for name in sly.fs.get_subdirs(directory)
    ]
    for subdirectory in subdirectories:
        subdirectory = os.path.abspath(subdirectory)
        sly.logger.debug(f"Processing subdirectory {subdirectory}")

        annotations_dir = os.path.join(subdirectory, "annotations")
        sly.fs.mkdir(annotations_dir)

        annotations_file_src = os.path.join(subdirectory, "_annotations.coco.json")
        annotations_file_dst = os.path.join(annotations_dir, "instances.json")
        sly.fs.copy_file(annotations_file_src, annotations_file_dst)
        sly.fs.silent_remove(annotations_file_src)

        images_dir = os.path.join(subdirectory, "images")
        sly.fs.mkdir(images_dir)

        images = sly.fs.list_files(subdirectory)
        for image in images:
            shutil.move(image, images_dir)

    sly.logger.info(f"Finished preparing COCO structure in {directory}")


def update_cells(project_id: int, **kwargs) -> None:
    """Updates cells in the projects table by project ID.
    Possible kwargs:
        - new_status: new status for the project
        - new_url: new Supervisely URL for the project

    :param project_id: project ID in CVAT for projects table to update
    :type project_id: int
    """
    key_cell_value = project_id
    key_column_name = "ID"
    if kwargs.get("new_status"):
        column_name = "COPYING STATUS"
        new_value = kwargs["new_status"]
    elif kwargs.get("new_url"):
        column_name = "SUPERVISELY URL"
        url = kwargs["new_url"]
        new_value = f"<a href='{url}' target='_blank'>{url}</a>"

    projects_table.update_cell_value(
        key_column_name, key_cell_value, column_name, new_value
    )


@stop_button.click
def stop_copying() -> None:
    """Stops copying process by setting continue_copying flag to False."""
    sly.logger.debug("Stop button is clicked.")

    g.STATE.continue_copying = False
    copy_button.text = "Stopping..."

    stop_button.hide()