from typing import List
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


# def check_connection() -> bool:
#     """Checks the connection to the Roboflow API used saved in the global state credentials.
#     Returns True if the connection was successful, False otherwise.

#     :return: result of the connection check
#     :rtype: bool
#     """
#     sly.logger.debug(
#         f"Will try to connect to Roboflow API at {g.STATE.roboflow_api_address} "
#         "to check the connection settings."
#     )
#     workspace =

#     # try:
#     #     workspace = get_workspace()
#     # except Exception as e:
#     #     sly.logger.error(f"Exception when calling Roboflow API: {e}")
#     #     return False

#     sly.logger.info(f"Connection was successful. Roboflow workspace: {workspace}.")
#     return True


# def cvat_data(**kwargs) -> Generator[CVATData, None, None]:
#     """Generator that yields CVATData objects for projects or tasks from CVAT API.
#     Each yielded object is a namedtuple with the following fields:
#         - entity: str (project or task)
#         - id: int (id of the project or task)
#         - name: str (name of the project or task)
#         - status: str (status of the project or task)
#         - owner_username: str (username of the owner of the project or task)
#         - labels_count: int (number of labels in the project or task)
#         - url: str (url of the project or task)

#     If no kwargs are passed, the generator yields projects data.
#     If kwargs contain project_id, the generator yields tasks data for the given project_id.

#     :yield: CVATData objects, representing projects or tasks from CVAT API
#     :rtype: Generator[CVATData, None, None]
#     """
#     if not kwargs:
#         # If no kwargs are passed, yield projects data.
#         method = "projects_api.list()"
#         entity = "project"
#     if kwargs.get("project_id"):
#         # If project_id is passed, yield tasks data for the given project_id.
#         method = f"tasks_api.list(project_id={kwargs['project_id']})"
#         entity = "task"

#     sly.logger.debug(f"Will try to retreive {method} from CVAT API.")

#     with ApiClient(get_configuration()) as api_client:
#         try:
#             (data, response) = eval(f"api_client.{method}")
#         except exceptions.ApiException as e:
#             sly.logger.error(f"Exception when calling CVAT API projects_api.list: {e}")
#             return

#     # Unused data for debugging purposes.
#     # Can be used to check the structure of the data returned by CVAT API
#     # and to compare number of data entries returned by CVAT API and by the generator.
#     count = data.get("count")
#     if count:
#         sly.logger.debug(f"API reponsed with {data['count']} data entries.")

#     results = data.get("results")
#     if not results:
#         sly.logger.debug("API reponsed with no data entries.")
#         return

#     for result in results:
#         try:
#             # To avoid AttributeError if the result doesn't have the field
#             # and to maintain equal structure of the yielded objects.
#             owner_username = result.get("owner").get("username")
#         except AttributeError:
#             owner_username = None
#         try:
#             # Same as for owner_username.
#             labels_count = result.get("labels").get("count")
#         except AttributeError:
#             labels_count = None

#         url = result.get("url")

#         # By default, CVAT API returns url with "/api/" in it, which can not
#         # be used to open the project or task in the browser.
#         url = url.replace("/api/", "/") if url else None

#         data_type = result.get("data_original_chunk_type")

#         yield CVATData(
#             entity=entity,
#             data_type=data_type,
#             id=result.get("id"),
#             name=result.get("name"),
#             status=result.get("status"),
#             owner_username=owner_username,
#             labels_count=labels_count,
#             url=url,
#         )


# def retreive_dataset(task_id: int) -> io.BufferedReader:
#     """Retreives the dataset from CVAT API for the given task_id and returns it as a bytes stream,
#     which can be used to save the dataset to the disk.

#     :param task_id: id of the task to retreive the dataset from CVAT API
#     :type task_id: int
#     :return: bytes stream with the dataset
#     :rtype: io.BufferedReader
#     """
#     with ApiClient(get_configuration()) as api_client:
#         try:
#             (data, response) = api_client.tasks_api.retrieve_dataset(
#                 format="CVAT for images 1.1",
#                 id=task_id,
#                 action="download",
#             )
#         except exceptions.ApiException as e:
#             sly.logger.error(f"Exception when calling CVAT API projects_api.list: {e}")
#             return

#     return data


# def retreive_formats() -> Dict[str, List[CVATFormat]]:
#     """Retreive all available formats from CVAT API (exporters and importers).
#     NOTE: This function is not used in the app, but it can be useful for debugging.

#     CVATFormat is a namedtuple with the following fields:
#         - dimension: str
#         - enabled: bool
#         - ext: str
#         - name: str
#         - version: str

#     :return: dictionary with exporters and importers keys and lists of CVATFormat objects as values
#     :rtype: Dict[str, List[CVATFormat]]
#     """
#     with ApiClient(get_configuration()) as api_client:
#         try:
#             (data, response) = api_client.server_api.retrieve_annotation_formats()
#         except exceptions.ApiException as e:
#             sly.logger.error(f"Exception when calling CVAT API projects_api.list: {e}")
#             return

#     exporters = data.get("exporters")
#     importers = data.get("importers")

#     formats = {
#         "exporters": [],
#         "importers": [],
#     }

#     for exporter in exporters:
#         formats["exporters"].append(
#             CVATFormat(
#                 dimension=exporter.get("dimension"),
#                 enabled=exporter.get("enabled"),
#                 ext=exporter.get("ext"),
#                 name=exporter.get("name"),
#                 version=exporter.get("version"),
#             )
#         )

#     for importer in importers:
#         formats["importers"].append(
#             CVATFormat(
#                 dimension=importer.get("dimension"),
#                 enabled=importer.get("enabled"),
#                 ext=importer.get("ext"),
#                 name=importer.get("name"),
#                 version=importer.get("version"),
#             )
#         )

#     return formats
