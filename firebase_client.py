"""
firebase_client.py — Firebase Admin SDK initializer.
Called once; subsequent calls return the cached app.
"""

import json
import os
import firebase_admin
from firebase_admin import credentials
from config import FIREBASE_SERVICE_ACCOUNT, FIREBASE_STORAGE_BUCKET

_initialized = False


def init_firebase():
    global _initialized
    if _initialized or firebase_admin._apps:
        _initialized = True
        return

    if not FIREBASE_SERVICE_ACCOUNT:
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT is not set. "
            "Add it to your .env file (path to JSON or raw JSON string)."
        )

    # Accept either a file path or a raw JSON string
    try:
        sa_dict = json.loads(FIREBASE_SERVICE_ACCOUNT)
        cred = credentials.Certificate(sa_dict)
    except (json.JSONDecodeError, ValueError):
        # Treat as file path
        cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT)

    firebase_admin.initialize_app(
        cred,
        {"storageBucket": FIREBASE_STORAGE_BUCKET},
    )
    _initialized = True
