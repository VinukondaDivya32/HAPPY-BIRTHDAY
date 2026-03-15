from PIL import Image
import io
import logging
import requests
import time
from flask import url_for
from blob_storage import get_thumbnail_url, upload_thumbnail
from drive_service import get_drive_service

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _download_with_retry(url, retries=3, timeout=10):
    """Downloads a file with retries and timeout."""
    for attempt in range(retries):
        try:
            response = requests.get(url, stream=True, timeout=timeout)
            response.raise_for_status()  # Raise an exception for bad status codes
            return response
        except requests.exceptions.RequestException as e:
            logger.warning(f"Download attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(1)  # Wait a bit before retrying
            else:
                logger.error("All download attempts failed.")
                return None

def generate_thumbnail(image_bytes):
    """
    Generates a thumbnail from image bytes.

    Args:
        image_bytes: The image data in bytes.

    Returns:
        Thumbnail image data in bytes, or None if generation fails.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.thumbnail((300, 300))
        thumb_io = io.BytesIO()
        img.save(thumb_io, format='JPEG', quality=85)
        thumb_io.seek(0)
        logger.info("Thumbnail generated successfully.")
        return thumb_io.read()
    except Exception as e:
        logger.error(f"Error generating thumbnail: {e}")
        return None

def get_or_create_thumbnail(file_id, filename):
    """
    Gets a thumbnail from Azure Blob Storage, creating it if it doesn't exist.

    Args:
        file_id: The Google Drive file ID.
        filename: The original filename.

    Returns:
        The URL of the thumbnail, or a fallback placeholder image URL.
    """
    fallback_url = url_for('static', filename='img/image-placeholder.png')
    thumbnail_blob_name = f"{file_id}_{filename}.jpg"
    
    # 1. Check if thumbnail exists in Azure Blob Storage
    thumbnail_url = get_thumbnail_url(thumbnail_blob_name)
    if thumbnail_url:
        logger.info(f"Thumbnail '{thumbnail_blob_name}' found in blob cache.")
        return thumbnail_url

    logger.info(f"Thumbnail for '{filename}' not in cache. Generating...")

    # 2. If not, download the image from Google Drive
    drive_service = get_drive_service()
    if not drive_service:
        logger.error("Google Drive service not available.")
        return fallback_url

    try:
        request = drive_service.files().get_media(fileId=file_id)
        downloader = _download_with_retry(request.uri)
        
        if not downloader:
            logger.error(f"Failed to download file from Google Drive after multiple retries.")
            return fallback_url

        fh = io.BytesIO()
        for chunk in downloader.iter_content(chunk_size=8192):
            fh.write(chunk)
        fh.seek(0)
        image_bytes = fh.read()

        # 3. Generate thumbnail using Pillow
        thumbnail_bytes = generate_thumbnail(image_bytes)
        if not thumbnail_bytes:
            return fallback_url

        # 4. Upload thumbnail to Azure Blob
        thumbnail_url = upload_thumbnail(thumbnail_blob_name, thumbnail_bytes)
        if not thumbnail_url:
            logger.error(f"Failed to upload thumbnail '{thumbnail_blob_name}'.")
            return fallback_url
            
        logger.info(f"Thumbnail pipeline completed for '{filename}'.")
        return thumbnail_url

    except Exception as e:
        logger.error(f"An error occurred in get_or_create_thumbnail for '{filename}': {e}")
        return fallback_url
