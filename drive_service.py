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
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_drive_service():
    """Initializes and returns a Google Drive API service object."""
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Error refreshing credentials: {e}")
                creds = None
        if not creds:
            try:
                flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                logger.error(f"Error with authorization flow: {e}")
                return None
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Error building Drive service: {e}")
        return None


def get_drive_images(folder_id):
    """
    Fetches a list of images from a specified Google Drive folder.

    Args:
        folder_id: The ID of the Google Drive folder.

    Returns:
        A list of dictionaries, where each dictionary represents an image
        and contains 'file_id', 'filename', and 'mime_type'.
        Returns an empty list if there's an error or no files are found.
    """
    service = get_drive_service()
    if not service:
        return []

    try:
        query = f"'{folder_id}' in parents and (mimeType='image/jpeg' or mimeType='image/png' or mimeType='video/mp4')"
        results = service.files().list(
            q=query,
            pageSize=100,
            fields="nextPageToken, files(id, name, mimeType)"
        ).execute()

        items = results.get('files', [])
        
        if not items:
            logger.info("No files found in the specified Google Drive folder.")
            return []

        return [{'file_id': item['id'], 'filename': item['name'], 'mime_type': item['mimeType']} for item in items]

    except Exception as e:
        logger.error(f"An error occurred while fetching from Google Drive: {e}")
        return []

if __name__ == '__main__':
    # Replace with your Google Drive Folder ID
    DRIVE_FOLDER_ID = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
    if DRIVE_FOLDER_ID:
        images = get_drive_images(DRIVE_FOLDER_ID)
        if images:
            print("Fetched images from Google Drive:")
            for img in images:
                print(f"  - ID: {img['file_id']}, Name: {img['filename']}, MIME Type: {img['mime_type']}")
    else:
        print("Please set the GOOGLE_DRIVE_FOLDER_ID environment variable.")

