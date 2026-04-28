"""
functions/main.py — Firebase Cloud Function (HTTP trigger)
Person 2: Serverless Backend

Deploy command:
    gcloud functions deploy detect_image \
        --runtime python311 \
        --trigger-http \
        --allow-unauthenticated \
        --set-env-vars SIGHTENGINE_API_USER=xxx,SIGHTENGINE_API_SECRET=yyy \
        --region us-central1

OR via Firebase CLI:
    firebase deploy --only functions
"""

import base64
import hashlib
import json
import os
import random
from datetime import datetime

import firebase_admin
import functions_framework
import requests
from firebase_admin import firestore

# ---------------------------------------------------------------------------
# Init Firebase (runs once per cold start)
# ---------------------------------------------------------------------------
if not firebase_admin._apps:
    firebase_admin.initialize_app()

CONFIDENCE_THRESHOLD   = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
SIGHTENGINE_API_USER   = os.getenv("SIGHTENGINE_API_USER", "")
SIGHTENGINE_API_SECRET = os.getenv("SIGHTENGINE_API_SECRET", "")

_CORS_HEADERS = {
    "Access-Control-Allow-Origin":  "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
@functions_framework.http
def detect_image(request):
    """
    HTTP Cloud Function handler.

    Expected JSON body:
        {
            "image_base64": "<base64-encoded image bytes>",
            "filename":     "photo.jpg"          (optional)
        }

    Returns:
        {
            "label":          "AI-Generated" | "Real",
            "confidence":     0.93,
            "ai_probability": 0.93,
            "source":         "Sightengine API (Cloud Function)",
            "filename":       "photo.jpg",
            "timestamp":      "2025-04-14T10:30:00",
            "size_kb":        142.5,
            "threshold":      0.7
        }
    """
    # Pre-flight CORS
    if request.method == "OPTIONS":
        return ("", 204, _CORS_HEADERS)

    try:
        body = request.get_json(silent=True)
        if not body or "image_base64" not in body:
            return _error("Missing required field: image_base64", 400)

        image_bytes = base64.b64decode(body["image_base64"])
        filename    = body.get("filename", "image.jpg")

        # --- Detection ---
        if SIGHTENGINE_API_USER and SIGHTENGINE_API_SECRET:
            detection = _sightengine_detect(image_bytes)
        else:
            detection = _demo_detect(image_bytes)

        # --- Build result ---
        result = {
            **detection,
            "filename":  filename,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "size_kb":   round(len(image_bytes) / 1024, 2),
            "threshold": CONFIDENCE_THRESHOLD,
        }

        # --- Persist to Firestore ---
        db = firestore.client()
        db.collection("detections").add(result)

        return (json.dumps(result), 200, _CORS_HEADERS)

    except Exception as exc:  # noqa: BLE001
        return _error(str(exc), 500)


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------

def _sightengine_detect(image_bytes: bytes) -> dict:
    files = {"media": ("image.jpg", image_bytes, "image/jpeg")}
    data  = {
        "models":     "genai",
        "api_user":   SIGHTENGINE_API_USER,
        "api_secret": SIGHTENGINE_API_SECRET,
    }
    resp = requests.post(
        "https://api.sightengine.com/1.0/check.json",
        files=files, data=data, timeout=15,
    )
    resp.raise_for_status()
    result = resp.json()

    if result.get("status") != "success":
        msg = result.get("error", {}).get("message", "Unknown API error")
        raise RuntimeError(f"Sightengine: {msg}")

    ai_prob    = float(result["type"]["ai_generated"])
    label      = "AI-Generated" if ai_prob >= CONFIDENCE_THRESHOLD else "Real"
    confidence = ai_prob if label == "AI-Generated" else 1.0 - ai_prob

    return {
        "label":          label,
        "confidence":     round(confidence, 4),
        "ai_probability": round(ai_prob, 4),
        "source":         "Sightengine API (Cloud Function)",
    }


def _demo_detect(image_bytes: bytes) -> dict:
    """Deterministic simulation — same image always returns the same result."""
    seed = int(hashlib.md5(image_bytes).hexdigest()[:8], 16)
    rng  = random.Random(seed)

    ai_prob    = rng.uniform(0.05, 0.98)
    label      = "AI-Generated" if ai_prob >= CONFIDENCE_THRESHOLD else "Real"
    confidence = ai_prob if label == "AI-Generated" else 1.0 - ai_prob

    return {
        "label":          label,
        "confidence":     round(confidence, 4),
        "ai_probability": round(ai_prob, 4),
        "source":         "Demo Mode (Cloud Function)",
    }


def _error(message: str, status: int):
    return (json.dumps({"error": message}), status, _CORS_HEADERS)
