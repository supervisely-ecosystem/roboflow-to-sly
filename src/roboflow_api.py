from typing import List
import supervisely as sly
import roboflow
import requests

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
    save_path: str,
    export_format: str,
) -> bool:
    """Downloads the project from Roboflow API to the given save path in the given export format.

    :param project: Roboflow Project object
    :type project: roboflow.Project
    :param save_path: path to save the downloaded project
    :type save_path: str
    :param export_format: format to export the project
    :type export_format: str
    :return: True if the project was successfully downloaded, False otherwise
    :rtype: bool
    """
    sly.logger.info(
        f"Downloading project {project.name} from Roboflow API. "
        f"Export format: {export_format}, save path: {save_path}."
    )

    versions = project.versions()
    if not versions:
        sly.logger.warning(
            f"Project {project.name} has no versions. "
            "In order to download the project, it must have at least one version."
        )
        return False

    version = versions[-1]
    sly.logger.debug(f"Using latest version {version.version}.")

    request = (
        f"{g.STATE.roboflow_api_address}/{version.version}/"
        f"{export_format}?api_key={g.STATE.roboflow_api_key}"
    )
    sly.logger.info(
        f"Making request (API key hidden in logs) to {request.split('?')[0]}"
    )

    response = requests.request("GET", request)
    if response.status_code != 200:
        sly.logger.warning(f"Failed to download project: {response.text}")
        return False

    export = response.json().get("export")

    if not export:
        sly.logger.warning("Failed to download project: export data is empty.")
        return False

    sly.logger.debug(f"Successfully retrieved export data: {export}.")

    download_link = export.get("link")
    download_size = export.get("size")

    if not download_link:
        sly.logger.warning("Failed to download project: download link is empty.")
        return False

    sly.logger.info(f"Downloading {download_size} MB from {download_link}.")

    download_response = requests.request("GET", download_link)
    with open(save_path, "wb") as f:
        f.write(download_response.content)

    sly.logger.info(f"Successfully downloaded data to {save_path}.")

    return True
