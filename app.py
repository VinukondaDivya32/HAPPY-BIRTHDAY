import os
import json
import time
from flask import Flask, render_template, url_for, redirect, request, jsonify, session
import logging

# --- Service Imports ---
import drive_service
import thumbnail_service
import blob_storage
from blob_storage import AZURE_BLOB_CONTAINER

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
GOOGLE_DRIVE_FOLDER_ID = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
AZURE_STORAGE_CONNECTION_STRING = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-set-SECRET_KEY')

# --- Constants ---
PAGE_SIZE = 50
CACHE_DURATION = 300  # 5 minutes
THUMBNAIL_PRELOAD_LIMIT = 20 # Max new thumbnails per request

# --- In-memory cache for Google Drive file list ---
drive_cache = {
    'data': None,
    'expires': 0
}

app = Flask(__name__, static_folder='static')
app.secret_key = SECRET_KEY

# Favorites storage file
FAVORITES_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), 'favorites.json'))

# --- Favorite Management ---
def load_favorites():
    try:
        if not os.path.exists(FAVORITES_FILE):
            return set()
        with open(FAVORITES_FILE, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
            return set(data) if isinstance(data, list) else set()
    except Exception as e:
        logger.error(f"Error loading favorites: {e}")
    return set()

def save_favorites(favs):
    try:
        with open(FAVORITES_FILE, 'w', encoding='utf-8') as fh:
            json.dump(sorted(list(favs)), fh, indent=2)
    except Exception as e:
        logger.error(f"Error saving favorites: {e}")

# --- Main Routes ---
@app.route('/')
def root():
    return redirect(url_for('gallery'))

@app.route('/set_greeted', methods=['POST'])
def set_greeted():
    session['greeted'] = True
    return jsonify({'ok': True})

@app.route('/gallery')
def gallery():
    if not GOOGLE_DRIVE_FOLDER_ID or not AZURE_STORAGE_CONNECTION_STRING:
        return "Application is not configured. Set GOOGLE_DRIVE_FOLDER_ID and AZURE_STORAGE_CONNECTION_STRING.", 500

    # --- Caching for Google Drive file list ---
    now = time.time()
    if now > drive_cache['expires']:
        logger.info("Drive cache expired. Fetching file list from Google Drive.")
        drive_cache['data'] = drive_service.get_drive_images(GOOGLE_DRIVE_FOLDER_ID)
        drive_cache['expires'] = now + CACHE_DURATION
    else:
        logger.info("Using cached file list from Google Drive.")

    all_files = drive_cache['data'] or []

    # --- Pagination ---
    try:
        page = int(request.args.get('page', '1'))
    except ValueError:
        page = 1
    page = max(1, page)

    total_images = len(all_files)
    total_pages = max(1, (total_images + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages)

    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    paginated_files = all_files[start:end]

    # --- Prepare items for template with thumbnail preload limit ---
    gallery_items = []
    new_thumbnails_generated = 0
    for item in paginated_files:
        file_id = item['file_id']
        filename = item['filename']
        
        # Check if thumbnail exists without generating
        thumbnail_blob_name = f"{file_id}_{filename}.jpg"
        thumbnail_url = blob_storage.get_thumbnail_url(thumbnail_blob_name)

        if not thumbnail_url and new_thumbnails_generated < THUMBNAIL_PRELOAD_LIMIT:
            thumbnail_url = thumbnail_service.get_or_create_thumbnail(file_id, filename)
            if not thumbnail_url.endswith('image-placeholder.png'):
                 new_thumbnails_generated += 1
        elif not thumbnail_url:
            # If limit is reached, use a placeholder to avoid generating more
            thumbnail_url = url_for('static', filename='img/image-placeholder.png')

        image_url = f"https://drive.google.com/uc?id={file_id}"
        
        gallery_items.append({
            'id': file_id,
            'thumbnail_url': thumbnail_url,
            'image_url': image_url,
            'filename': filename,
            'type': 'video' if item['mime_type'].startswith('video') else 'image'
        })

    favorites = load_favorites()
    show_intro = not bool(session.get('greeted'))

    return render_template('gallery.html', 
                             images=gallery_items, 
                             current_path='', 
                             parent=None, 
                             page=page, 
                             total_pages=total_pages, 
                             favorites=favorites,
                             browse_ep='gallery',
                             show_intro=show_intro)

@app.route('/favorites')
def favorites_view():
    favorites = load_favorites()
    all_files = drive_service.get_drive_images(GOOGLE_DRIVE_FOLDER_ID) or []
    
    favorite_items = []
    for item in all_files:
        if item['file_id'] in favorites:
            file_id = item['file_id']
            filename = item['filename']
            
            thumbnail_url = thumbnail_service.get_or_create_thumbnail(file_id, filename)
            image_url = f"https://drive.google.com/uc?id={file_id}"
            
            favorite_items.append({
                'id': file_id,
                'thumbnail_url': thumbnail_url,
                'image_url': image_url,
                'filename': filename,
                'type': 'video' if item['mime_type'].startswith('video') else 'image'
            })

    return render_template('gallery.html', 
                             images=favorite_items, 
                             current_path='favorites', 
                             parent=None, 
                             page=1, 
                             total_pages=1, 
                             favorites=favorites, 
                             browse_ep='gallery')

@app.route('/toggle_favorite', methods=['POST'])
def toggle_favorite():
    data = request.get_json() or {}
    file_id = data.get('id')
    if not file_id:
        return jsonify({'error': 'missing file ID'}), 400
    
    favs = load_favorites()
    if file_id in favs:
        favs.remove(file_id)
        is_fav = False
    else:
        favs.add(file_id)
        is_fav = True
    
    save_favorites(favs)
    return jsonify({'is_favorite': is_fav, 'id': file_id})

@app.route('/reset_greeting')
def reset_greeting():
    session.pop('greeted', None)
    return redirect(url_for('gallery'))

# --- Debug and Healthcheck Routes ---
@app.route('/debug/drive')
def debug_drive():
    files = drive_service.get_drive_images(GOOGLE_DRIVE_FOLDER_ID)
    if files is None:
        return jsonify({"error": "Failed to fetch from Google Drive"}), 500
    
    return jsonify({
        "file_count": len(files),
        "files": [{'name': f['filename'], 'id': f['file_id'], 'mime_type': f['mime_type']} for f in files]
    })

@app.route('/debug/blob')
def debug_blob():
    blobs = blob_storage.list_blobs()
    return jsonify({
        "container_name": AZURE_BLOB_CONTAINER,
        "blob_count": len(blobs),
        "blobs": blobs
    })

@app.route('/health')
def health_check():
    # Check Google Drive
    drive_status = "connected"
    try:
        # A lightweight check
        drive_service.get_drive_service().about().get(fields='user').execute()
    except Exception as e:
        drive_status = f"disconnected: {e}"
        logger.error(f"Health check failed for Google Drive: {e}")

    # Check Azure Blob Storage
    blob_status = "connected"
    try:
        client = blob_storage.get_blob_service_client()
        if client:
            client.get_container_client(AZURE_BLOB_CONTAINER).get_container_properties()
        else:
            blob_status = "disconnected: client is None"
    except Exception as e:
        blob_status = f"disconnected: {e}"
        logger.error(f"Health check failed for Azure Blob: {e}")

    status_code = 200 if "connected" in drive_status and "connected" in blob_status else 503
    
    return jsonify({
        "status": "ok" if status_code == 200 else "error",
        "drive_api": drive_status,
        "azure_blob": blob_status
    }), status_code

if __name__ == '__main__':
    if not GOOGLE_DRIVE_FOLDER_ID:
        print("Warning: GOOGLE_DRIVE_FOLDER_ID is not set.")
    if not AZURE_STORAGE_CONNECTION_STRING:
        print("Warning: AZURE_STORAGE_CONNECTION_STRING is not set.")
    
    # For local development, you might need to run with `python app.py`
    # For production on Azure App Service, the command will be `gunicorn app:app`
    app.run(host='127.0.0.1', port=5000, debug=True)


