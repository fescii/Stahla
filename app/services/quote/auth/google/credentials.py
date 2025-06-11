import os
import logfire
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError  # Keep for potential future use

# SCOPES can be defined here or imported if they are centralized elsewhere.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']


def _get_google_credentials_internal(google_app_creds_path: str):
  """Loads Google Service Account credentials."""
  logfire.info("AuthService._get_google_credentials_internal: Entered method.")
  try:
    if google_app_creds_path:
      creds_path_config = google_app_creds_path
      logfire.info(
          f"AuthService._get_google_credentials_internal: Credentials path configured to: '{creds_path_config}'")

      # Ensure the path is absolute. If it's relative, it's usually relative to the CWD.
      # settings.GOOGLE_APPLICATION_CREDENTIALS is 'app/gcp.json'.
      # If CWD is project root, abspath will work.
      creds_path = os.path.abspath(creds_path_config)
      logfire.info(
          f"AuthService._get_google_credentials_internal: Absolute path for credentials: {creds_path}")

      if not os.path.exists(creds_path):
        logfire.error(
            f"AuthService._get_google_credentials_internal: Google credentials file NOT FOUND at: {creds_path}")
        raise FileNotFoundError(f"Credentials file not found: {creds_path}")

      logfire.info(
          f"AuthService._get_google_credentials_internal: Attempting to load credentials from file: {creds_path}")
      loaded_creds = service_account.Credentials.from_service_account_file(
          creds_path, scopes=SCOPES
      )
      logfire.info(
          "AuthService._get_google_credentials_internal: Successfully loaded credentials from file.")
      return loaded_creds
    else:
      logfire.info(
          "AuthService._get_google_credentials_internal: GOOGLE_APPLICATION_CREDENTIALS path not provided. Attempting ADC.")
      from google.auth import default  # Application Default Credentials
      logfire.info(
          "AuthService._get_google_credentials_internal: Attempting google.auth.default().")
      adc_creds, project = default(scopes=SCOPES)
      logfire.info(
          f"AuthService._get_google_credentials_internal: ADC obtained. Project: {project if project else 'Not determined'}")
      return adc_creds
  except FileNotFoundError as fnf_error:
    logfire.error(
        f"AuthService._get_google_credentials_internal: FileNotFoundError - {fnf_error}")
    raise RuntimeError(
        f"Could not initialize Google Sheets credentials due to FileNotFoundError: {fnf_error}") from fnf_error
  except Exception as e:
    logfire.error(
        f"AuthService._get_google_credentials_internal: Exception during credential loading - Type: {type(e).__name__}, Args: {e.args}", exc_info=True)
    raise RuntimeError(
        f"Could not initialize Google Sheets credentials due to: {type(e).__name__}") from e


def create_sheets_service(google_app_creds_path: str):
  """
  Initializes and returns a Google Sheets API service client.
  Relies on default HTTP transport handling by google-api-python-client.
  """
  logfire.info(
      "AuthService.create_sheets_service: Initializing Google Sheets service...")

  # Get credentials
  creds = _get_google_credentials_internal(google_app_creds_path)

  logfire.info(
      "AuthService.create_sheets_service: Building Google Sheets service with credentials (default transport).")
  try:
    # Pass the credentials object directly to the build function.
    # google-api-python-client and google-auth will handle transport creation.
    service = build('sheets', 'v4', credentials=creds, cache_discovery=False)

    logfire.info(
        "AuthService.create_sheets_service: Google Sheets API service built successfully.")
    return service
  except Exception as e:
    logfire.error(
        f"AuthService.create_sheets_service: Failed to build Google Sheets service - Type: {type(e).__name__}, Args: {e.args}", exc_info=True)
    # Propagate the error so the caller knows service creation failed.
    raise RuntimeError(
        f"Could not build Google Sheets service in auth.py due to: {type(e).__name__}") from e
