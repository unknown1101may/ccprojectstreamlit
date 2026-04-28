"""
backend.py — Person 2: Serverless Backend Logic

Flow when Firebase is configured:
    1. Upload image  → Firebase Storage
    2. Call Cloud Function (HTTP) with image bytes → AI detection + Firestore save
    3. Return result to Streamlit

Flow in local/demo mode:
    1. Run detection locally via detector.py
    2. Store result in Streamlit session state
"""

import base64

import requests
import streamlit as st
from datetime import datetime

from config import (
    CONFIDENCE_THRESHOLD,
    FIREBASE_ENABLED,
    CLOUD_FUNCTION_URL,
)
from detector import get_detector


# ---------------------------------------------------------------------------
# Core handler — mimics a serverless function signature
# ---------------------------------------------------------------------------

def process_image(image_bytes: bytes, filename: str) -> dict:
    """
    Main processing pipeline.
    Routes to Cloud Function if configured, otherwise processes locally.

    Decision logic applied in both paths:
        if ai_probability >= CONFIDENCE_THRESHOLD:
            result = "AI-Generated"
        else:
            result = "Real"
    """
    if FIREBASE_ENABLED and CLOUD_FUNCTION_URL:
        return _call_cloud_function(image_bytes, filename)
    return _process_locally(image_bytes, filename)


def _call_cloud_function(image_bytes: bytes, filename: str) -> dict:
    """Send image to Firebase Cloud Function via HTTP POST."""
    payload = {
        "image_base64": base64.b64encode(image_bytes).decode("utf-8"),
        "filename":     filename,
    }
    try:
        response = requests.post(CLOUD_FUNCTION_URL, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        raise RuntimeError("Cloud Function request timed out.")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Cloud Function error: {e.response.text}")


def _process_locally(image_bytes: bytes, filename: str) -> dict:
    """Local fallback — runs detection in-process."""
    detector = get_detector()
    detection = detector.detect(image_bytes)
    return {
        **detection,
        "filename":  filename,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "size_kb":   round(len(image_bytes) / 1024, 2),
        "threshold": CONFIDENCE_THRESHOLD,
    }


# ---------------------------------------------------------------------------
# Storage upload (only when Firebase is enabled)
# ---------------------------------------------------------------------------

def upload_to_storage(image_bytes: bytes, filename: str) -> tuple[str, str]:
    """
    Upload image to Firebase Storage.
    Returns (public_url, storage_path).
    """
    from firebase_storage import upload_image
    return upload_image(image_bytes, filename)


# ---------------------------------------------------------------------------
# History — Firestore when available, session state as fallback
# ---------------------------------------------------------------------------

def save_result(result: dict) -> None:
    """Persist result to Firestore (if Firebase enabled) and session state."""
    if FIREBASE_ENABLED:
        try:
            from firebase_db import save_result as db_save
            db_save(result)
        except Exception:
            pass  # Don't crash the UI if Firestore write fails

    # Always keep a session-state copy for instant UI updates
    if "detection_history" not in st.session_state:
        st.session_state.detection_history = []
    st.session_state.detection_history.insert(0, result)
    st.session_state.detection_history = st.session_state.detection_history[:50]


def get_history() -> list:
    """Read history from Firestore if available, else session state."""
    if FIREBASE_ENABLED:
        try:
            from firebase_db import get_all_results
            return get_all_results()
        except Exception:
            pass
    return st.session_state.get("detection_history", [])


def clear_history() -> None:
    if FIREBASE_ENABLED:
        try:
            from firebase_db import clear_all_results
            clear_all_results()
        except Exception:
            pass
    st.session_state.detection_history = []
