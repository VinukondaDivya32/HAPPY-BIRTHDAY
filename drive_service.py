import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import google_auth_oauthlib.flow
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Google Drive API v3 ---
import os
import logging
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import google_auth_oauthlib.flow

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Google Drive API v3 ---
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


def _token_path_candidates():
    """Return list of paths to look for token.json (order of preference)."""
    paths = []
    env_path = os.environ.get('GOOGLE_TOKEN_PATH')
    if env_path:
        paths.append(env_path)
    # Common App Service path
    paths.append('/home/site/wwwroot/token.json')
    # Current working directory
    paths.append(os.path.join(os.getcwd(), 'token.json'))
    # Project root (script directory)
    paths.append(os.path.join(os.path.dirname(__file__), 'token.json'))
    return paths


def _find_token_path():
    for p in _token_path_candidates():
        try:
            if p and os.path.exists(p):
                return p
        except Exception:
            continue
    return None


def load_credentials(token_path=None):
    """Load credentials from token file; returns Credentials or None."""
    if not token_path:
        token_path = _find_token_path()
    if not token_path:
        logger.info('No token.json found in expected locations.')
        return None

    try:
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        logger.info(f'Loaded credentials from {token_path}')
        creds._token_path = token_path
        return creds
    except Exception as e:
        logger.warning(f'Failed to load credentials from {token_path}: {e}')
        return None


def save_credentials(creds, token_path=None):
    """Save credentials to token file; returns True on success."""
    if not token_path:
        token_path = _find_token_path() or os.path.join(os.getcwd(), 'token.json')

    try:
        with open(token_path, 'w') as fh:
            fh.write(creds.to_json())
        try:
            os.chmod(token_path, 0o600)
        except Exception:
            pass
        logger.info(f'Saved credentials to {token_path}')
        return True
    except Exception as e:
        logger.error(f'Failed to save credentials to {token_path}: {e}')
        return False


def get_drive_service():
    """Return an authorized Google Drive service or None.

    Behavior:
    - Loads credentials from token.json (looks in several paths including
      /home/site/wwwroot/token.json for Azure App Service).
    - Refreshes tokens if expired and refresh_token is available.
    - Returns None if no valid credentials are available.
    """
    creds = load_credentials()

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Persist refreshed token to same path
            token_path = getattr(creds, '_token_path', None) or _find_token_path()
            if token_path:
                save_credentials(creds, token_path)
        except Exception as e:
            logger.warning(f'Failed to refresh credentials: {e}')
            creds = None

    if not creds:
        logger.error('No valid Google OAuth2 credentials available. Create token.json locally or run the OAuth web flow.')
        return None

    try:
        service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        return service
    except Exception as e:
        logger.error(f'Error building Drive service: {e}')
        return None


def get_drive_images(folder_id):
    """List image and video files in a Google Drive folder (paginated).

    Returns list of dicts: {'file_id','filename','mime_type'} or [] on error.
    """
    service = get_drive_service()
    if not service:
        return []

    results = []
    try:
        query = (
            f"'{folder_id}' in parents and (mimeType contains 'image/' or mimeType contains 'video/')"
        )
        page_token = None
        while True:
            resp = service.files().list(
                q=query,
                pageSize=100,
                fields='nextPageToken, files(id, name, mimeType)',
                pageToken=page_token
            ).execute()

            items = resp.get('files', [])
            for item in items:
                results.append({'file_id': item['id'], 'filename': item['name'], 'mime_type': item['mimeType']})

            page_token = resp.get('nextPageToken')
            if not page_token:
                break

        if not results:
            logger.info('No files found in Drive folder.')
        return results

    except Exception as e:
        logger.error(f'Error listing Drive files: {e}')
        return []


if __name__ == '__main__':
    DRIVE_FOLDER_ID = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
    if not DRIVE_FOLDER_ID:
        print('Set GOOGLE_DRIVE_FOLDER_ID in environment.')
    else:
        images = get_drive_images(DRIVE_FOLDER_ID)
        if images:
            for img in images:
                print(f"{img['file_id']}	{img['filename']}	{img['mime_type']}")
        else:
            print('No images found or failed to connect to Drive.')

