import os
from typing import List, Optional
import supervisely as sly
import roboflow

import src.globals as g


def get_configuration():
    try:
        return roboflow.Roboflow(api_key=g.STATE.roboflow_api_key)
    except Exception as e:
        sly.logger.error(f"Exception when calling Roboflow API: {e}")
        return


def get_workspace() -> roboflow.Workspace:
    """Returns Roboflow Workspace object from API when using saved in the global state credentials.

    :return: Roboflow Workspace object
    :rtype: roboflow.Workspace
    """
    sly.logger.debug(
        f"Getting Roboflow Workspace object for {g.STATE.roboflow_api_address}."
    )

    rf = get_configuration()
    if not rf:
        return
    workspace = rf.workspace()
    if not workspace:
        return
    return workspace


def get_projects(workspace: roboflow.Workspace = None) -> List[roboflow.Project]:
    if workspace is None:
        workspace = get_workspace()
    project_names = workspace.projects()
    rf = get_configuration()
    return [rf.project(project_name) for project_name in project_names]


def download_project(
    project: roboflow.Project,
    save_dir: str,
    export_format: str,
) -> Optional[str]:
    """Downloads and extracts a Roboflow project using the SDK.

    :param project: Roboflow Project object
    :type project: roboflow.Project
    :param save_dir: directory where the project will be downloaded
    :type save_dir: str
    :param export_format: format to export the project (e.g. "coco", "folder")
    :type export_format: str
    :return: path to the extracted project directory, or None on failure
    :rtype: Optional[str]
    """
    versions = project.versions()
    if not versions:
        sly.logger.warning(
            f"Project {project.name} has no versions. "
            "In order to download the project, it must have at least one version."
        )
        return None

    # versions()[-1].version is the full ID like "workspace/project/1";
    latest = versions[-1]
    version_number = int(os.path.basename(str(latest.version)))
    version = project.version(version_number)

    sly.logger.debug(f"Using latest version {version_number}.")
    sly.logger.info(
        f"Downloading project {project.name} in {export_format} format to {save_dir}."
    )

    try:
        dataset = version.download(export_format, location=save_dir)
        extract_path = _find_data_root(dataset.location, export_format)
        sly.logger.info(
            f"Successfully downloaded project {project.name} to {extract_path}."
        )
        return extract_path
    except Exception as e:
        sly.logger.error(f"Failed to download project {project.name}: {e}")
        return None


def _find_data_root(base_dir: str, export_format: str) -> str:
    """Locate the actual data directory inside base_dir.

    Roboflow SDK sometimes extracts the zip into a named subdirectory inside
    the requested location (e.g. location/pipe_root-1/).  Walk up to two
    levels deep to find the real data root:
    - For COCO: a directory whose immediate children include 'train', 'valid',
      or 'test' subdirectories that contain '_annotations.coco.json'.
    - For folder (classification): a directory whose immediate children include
      'train', 'valid', or 'test' subdirectories with image files.

    Returns base_dir unchanged when the data is already at the top level.
    """
    def _has_split_dirs(directory: str) -> bool:
        subdirs = {name for name in os.listdir(directory) if os.path.isdir(os.path.join(directory, name))}
        return bool(subdirs & {"train", "valid", "test"})

    if _has_split_dirs(base_dir):
        return base_dir

    # Check one level deeper (SDK nested the contents)
    for name in os.listdir(base_dir):
        candidate = os.path.join(base_dir, name)
        if os.path.isdir(candidate) and _has_split_dirs(candidate):
            sly.logger.debug(f"Found actual data root at {candidate} (nested inside {base_dir}).")
            return candidate

    sly.logger.warning(
        f"Could not locate data root in {base_dir}. Listing: {os.listdir(base_dir)}. "
        "Returning base_dir as fallback."
    )
    return base_dir
