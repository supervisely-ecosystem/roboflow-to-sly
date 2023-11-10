import os

from collections import namedtuple
import supervisely as sly

from dotenv import load_dotenv

ABSOLUTE_PATH = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(ABSOLUTE_PATH)
sly.logger.debug(f"Absolute path: {ABSOLUTE_PATH}, parent dir: {PARENT_DIR}")

if sly.is_development():
    # * For convinient development, has no effect in the production.
    local_env_path = os.path.join(PARENT_DIR, "local.env")
    supervisely_env_path = os.path.expanduser("~/supervisely.env")
    sly.logger.debug(
        "Running in development mode. Will load .env files... "
        f"Local .env path: {local_env_path}, Supervisely .env path: {supervisely_env_path}"
    )

    if os.path.exists(local_env_path) and os.path.exists(supervisely_env_path):
        sly.logger.debug("Both .env files exists. Will load them.")
        load_dotenv(local_env_path)
        load_dotenv(supervisely_env_path)
    else:
        sly.logger.warning("One of the .env files is missing. It may cause errors.")

api = sly.Api.from_env()

TEMP_DIR = os.path.join(PARENT_DIR, "temp")

# * Directory, where downloaded as archives Roboflow data will be stored.
ARCHIVE_DIR = os.path.join(TEMP_DIR, "archives")

# * Directory, where unpacked Roboflow data will be stored.
UNPACKED_DIR = os.path.join(TEMP_DIR, "unpacked")

# * Directory, where converted Supervisely data will be stored.
CONVERTED_DIR = os.path.join(TEMP_DIR, "converted")

sly.fs.mkdir(ARCHIVE_DIR, remove_content_if_exists=True)
sly.fs.mkdir(UNPACKED_DIR, remove_content_if_exists=True)
sly.fs.mkdir(CONVERTED_DIR, remove_content_if_exists=True)
sly.logger.debug(
    f"Archive dir: {ARCHIVE_DIR}, unpacked dir: {UNPACKED_DIR}, converted dir: {CONVERTED_DIR}"
)

DEFAULT_API_ADDRESS = "https://api.roboflow.com"
DEFAULT_APP_ADDRESS = "https://app.roboflow.com"


class State:
    def __init__(self):
        self.selected_team = sly.env.team_id()
        self.selected_workspace = sly.env.workspace_id()

        # Will be set to True, if the app will be launched from .env file in Supervisely.
        self.loaded_from_env = False

        # Roboflow credentials to access the API.
        self.roboflow_api_address = None
        self.roboflow_api_key = None

        self.projects = {}
        self.selected_projects = []

        # Will be set to False if the cancel button will be pressed.
        # Sets to True on every click on the "Copy" button.
        self.continue_copying = True

    def clear_roboflow_credentials(self):
        """Clears the Roboflow credentials and sets them to None."""

        sly.logger.debug("Clearing Roboflow credentials...")
        self.roboflow_api_address = None
        self.roboflow_api_key = None

    def load_from_env(self):
        """Downloads the .env file from Supervisely and reads the Roboflow credentials from it."""
        try:
            api.file.download(
                STATE.selected_team, ROBOFLOW_ENV_TEAMFILES, ROBOFLOW_ENV_FILE
            )
        except Exception as e:
            sly.logger.warning(f"Failed to download .env file: {e}")
            return

        sly.logger.debug(
            ".env file downloaded successfully. Will read the credentials."
        )

        load_dotenv(ROBOFLOW_ENV_FILE)

        self.roboflow_api_address = os.getenv(
            "ROBOFLOW_API_ADDRESS", DEFAULT_API_ADDRESS
        )
        self.roboflow_api_key = os.getenv("ROBOFLOW_API_KEY")
        sly.logger.debug(
            "Roboflow credentials readed successfully. "
            f"API address: {self.roboflow_api_address}, API key is hidden in logs. "
            "Will check the connection."
        )
        self.loaded_from_env = True


STATE = State()
sly.logger.debug(
    f"Selected team: {STATE.selected_team}, selected workspace: {STATE.selected_workspace}"
)

# * Local path to the .env file with credentials, after downloading it from Supervisely.
ROBOFLOW_ENV_FILE = os.path.join(PARENT_DIR, "roboflow.env")
sly.logger.debug(f"Path to the local roboflow.env file: {ROBOFLOW_ENV_FILE}")

# * Path to the .env file with credentials (on Team Files).
# While local development can be set in local.env file with: context.slyFile = "/.env/roboflow.env"
ROBOFLOW_ENV_TEAMFILES = sly.env.file(raise_not_found=False)
sly.logger.debug(f"Path to the TeamFiles from environment: {ROBOFLOW_ENV_TEAMFILES}")

CopyingStatus = namedtuple("CopyingStatus", ["copied", "error", "waiting", "working"])
COPYING_STATUS = CopyingStatus("✅ Copied", "❌ Error", "⏳ Waiting", "🔄 Working")

if ROBOFLOW_ENV_TEAMFILES:
    sly.logger.debug(".env file is provided, will try to download it.")
    STATE.load_from_env()
