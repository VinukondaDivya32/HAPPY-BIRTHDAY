import os
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Azure Blob Storage ---
AZURE_STORAGE_CONNECTION_STRING = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
AZURE_BLOB_CONTAINER = os.environ.get('AZURE_BLOB_CONTAINER', 'thumbnails')

def get_blob_service_client():
    """Initializes and returns a BlobServiceClient."""
    if not AZURE_STORAGE_CONNECTION_STRING:
        logger.error("AZURE_STORAGE_CONNECTION_STRING is not set.")
        return None
    try:
        return BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    except Exception as e:
        logger.error(f"Error creating BlobServiceClient: {e}")
        return None

def upload_thumbnail(blob_name, image_bytes):
    """
    Uploads a thumbnail to Azure Blob Storage.

    Args:
        blob_name: The name of the blob (e.g., the filename of the thumbnail).
        image_bytes: The thumbnail image data in bytes.

    Returns:
        The URL of the uploaded blob, or None if the upload fails.
    """
    blob_service_client = get_blob_service_client()
    if not blob_service_client:
        return None

    try:
        blob_client = blob_service_client.get_blob_client(container=AZURE_BLOB_CONTAINER, blob=blob_name)
        
        # Check if blob exists
        if blob_client.exists():
            logger.info(f"Thumbnail '{blob_name}' already exists in Azure Blob Storage.")
            return blob_client.url

        blob_client.upload_blob(image_bytes, overwrite=True)
        logger.info(f"Uploaded thumbnail '{blob_name}' to Azure Blob Storage.")
        return blob_client.url
    except Exception as e:
        logger.error(f"An error occurred while uploading to Azure Blob Storage: {e}")
        return None

def get_thumbnail_url(blob_name):
    """
    Gets the URL of a thumbnail from Azure Blob Storage.

    Args:
        blob_name: The name of the blob.

    Returns:
        The URL of the blob, or None if it doesn't exist.
    """
    blob_service_client = get_blob_service_client()
    if not blob_service_client:
        return None
        
    try:
        blob_client = blob_service_client.get_blob_client(container=AZURE_BLOB_CONTAINER, blob=blob_name)
        if blob_client.exists():
            return blob_client.url
        else:
            logger.info(f"Thumbnail '{blob_name}' not found in Azure Blob Storage.")
            return None
    except Exception as e:
        logger.error(f"An error occurred while checking for blob: {e}")
        return None

def list_blobs():
    """Lists all blobs in the container."""
    blob_service_client = get_blob_service_client()
    if not blob_service_client:
        return []
    
    try:
        container_client = blob_service_client.get_container_client(AZURE_BLOB_CONTAINER)
        blob_list = container_client.list_blobs()
        return [blob.name for blob in blob_list]
    except Exception as e:
        logger.error(f"Error listing blobs: {e}")
        return []

if __name__ == '__main__':
    # Example usage:
    if AZURE_STORAGE_CONNECTION_STRING:
        # Create a dummy image file for testing
        dummy_image_data = b"dummy image data"
        dummy_blob_name = "test_thumbnail.jpg"

        # Test upload
        url = upload_thumbnail(dummy_blob_name, dummy_image_data)
        if url:
            print(f"Uploaded to: {url}")

        # Test get URL
        url_check = get_thumbnail_url(dummy_blob_name)
        if url_check:
            print(f"Retrieved URL: {url_check}")
        else:
            print("Could not retrieve URL.")
    else:
        print("Please set the AZURE_STORAGE_CONNECTION_STRING environment variable.")
