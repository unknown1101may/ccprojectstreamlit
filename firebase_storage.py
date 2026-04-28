"""
firebase_storage.py — Upload images to Firebase Storage.
Returns a public URL and the Storage path for the uploaded file.
"""

import uuid
from datetime import datetime
from firebase_admin import storage
from firebase_client import init_firebase


def upload_image(image_bytes: bytes, filename: str) -> tuple[str, str]:
    """
    Upload image bytes to Firebase Storage.

    Returns
    -------
    (public_url, storage_path)
    """
    init_firebase()

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    uid = str(uuid.uuid4())[:8]
    storage_path = f"uploads/{timestamp}_{uid}.{ext}"

    bucket = storage.bucket()
    blob = bucket.blob(storage_path)
    blob.upload_from_string(image_bytes, content_type=f"image/{ext}")
    blob.make_public()

    return blob.public_url, storage_path
