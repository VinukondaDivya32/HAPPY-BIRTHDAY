# Local Flask Photo Gallery

This small Flask app serves images from an external folder (for example your local Google Drive sync folder) instead of using Flask's default `static` image folder.

How to update the gallery folder path

- Edit `app.py` and change the `GALLERY_DIR` variable near the top of the file to your folder path, e.g. `G:\My Drive\MyGallery`.
- Or set the environment variable `GALLERY_DIR` before running the app.

Quick start (Windows PowerShell)

```powershell
python -m pip install -r requirements.txt
$env:GALLERY_DIR = 'G:\My Drive\MyGallery'    # optional: set your path here
python app.py
``` 

Open http://127.0.0.1:5000 in your browser.

Notes
- The app will recursively scan the gallery folder for common image extensions.
- Images are served through the `/images/<path>` route which ensures requests stay inside the configured folder.
