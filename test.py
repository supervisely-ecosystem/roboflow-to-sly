import os
import roboflow
import requests

import supervisely as sly

from rich.console import Console

console = Console()

ROBOFLOW_API = "https://api.roboflow.com"
API_KEY = "qQSymt60UTnQV1qGZsfN"
CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
ARCHIVE_DIR = os.path.join(CURRENT_DIR, "archives")
UNPACKED_DIR = os.path.join(CURRENT_DIR, "unpacked")

try:
    rf = roboflow.Roboflow(api_key=API_KEY)
    console.log("Roboflow API connected")
except RuntimeError as e:
    console.print(e)
    console.log("Roboflow API connection failed")
    exit()

sly.fs.mkdir(ARCHIVE_DIR, remove_content_if_exists=True)
console.log(f"Created {ARCHIVE_DIR}")
sly.fs.mkdir(UNPACKED_DIR, remove_content_if_exists=True)
console.log(f"Created {UNPACKED_DIR}")


def get_workspace():
    return rf.workspace()


def get_projects(workspace):
    return workspace.projects()


def download_project(
    project: roboflow.Project,
    save_path: str,
    export_format: str = "coco",
):
    versions = project.versions()
    if not versions:
        # TODO: Log error
        return

    console.log(f"Retrieved {len(versions)} versions")
    version = versions[-1]
    console.log(f"Using latest version {version.version}")

    request = f"{ROBOFLOW_API}/{version.version}/{export_format}?api_key={API_KEY}"
    console.log(f"Making request (API key hidden in logs) to {request.split('?')[0]}")

    response = requests.request("GET", request)
    if response.status_code != 200:
        # TODO: Log error
        console.print(response)
        return

    console.print(f"Response: {response}")

    export = response.json().get("export")

    if not export:
        # TODO: Log error
        return

    console.log(f"Successfully retrieved export data: {export}")

    download_link = export.get("link")
    download_size = export.get("size")

    if not download_link:
        # TODO: Log error
        return

    console.log(f"Downloading {download_size} MB from {download_link}")

    download_response = requests.request("GET", download_link)
    with open(save_path, "wb") as f:
        f.write(download_response.content)

    console.log(f"Successfully downloaded data to {save_path}")

    return save_path


if __name__ == "__main__":
    console.log("Script started")

    workspace = get_workspace()
    projects = get_projects(workspace)

    console.log(f"Retrieved {len(projects)} projects")

    for project in projects:
        project = rf.project(project)
        save_path = os.path.join(ARCHIVE_DIR, f"{project.name}.zip")
        unpacked_path = os.path.join(UNPACKED_DIR, project.name)
        download_project(project, save_path)
        console.log(f"Saved project {project.name} to {save_path}")

        sly.fs.mkdir(unpacked_path, remove_content_if_exists=True)
        console.log(f"Created {unpacked_path}")

        sly.fs.unpack_archive(save_path, unpacked_path)
        console.log(f"Unpacked {save_path} to {unpacked_path}")

    console.log("Script finished")
