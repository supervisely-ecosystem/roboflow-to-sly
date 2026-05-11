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

    version = versions[-1]
    sly.logger.debug(f"Using latest version {version.version}.")
    sly.logger.info(
        f"Downloading project {project.name} in {export_format} format to {save_dir}."
    )

    try:
        dataset = version.download(export_format, location=save_dir)
        sly.logger.info(
            f"Successfully downloaded project {project.name} to {dataset.location}."
        )
        return dataset.location
    except Exception as e:
        sly.logger.error(f"Failed to download project {project.name}: {e}")
        return None
