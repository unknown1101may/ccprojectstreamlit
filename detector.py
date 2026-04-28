"""
detector.py — Person 3: AI Detection Module
Responsibility: Integrate detection API, process image, return label + confidence.

Supports two modes:
  1. SightengineDetector  — real API (free tier: 500 ops/month)
  2. DemoDetector         — deterministic simulation (no API key needed)
"""

import hashlib
import random
import requests
from config import (
    CONFIDENCE_THRESHOLD,
    SIGHTENGINE_API_USER,
    SIGHTENGINE_API_SECRET,
    DETECTION_MODE,
)


class SightengineDetector:
    """
    Calls the Sightengine AI-generated image detection API.
    Docs: https://sightengine.com/docs/genai
    Free tier: 500 API calls/month.
    """

    API_URL = "https://api.sightengine.com/1.0/check.json"

    def detect(self, image_bytes: bytes) -> dict:
        files = {"media": ("image.jpg", image_bytes, "image/jpeg")}
        data = {
            "models": "genai",
            "api_user": SIGHTENGINE_API_USER,
            "api_secret": SIGHTENGINE_API_SECRET,
        }

        try:
            response = requests.post(self.API_URL, files=files, data=data, timeout=15)
            response.raise_for_status()
            result = response.json()
        except requests.exceptions.Timeout:
            raise RuntimeError("Sightengine API request timed out.")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Network error: {e}")

        if result.get("status") != "success":
            msg = result.get("error", {}).get("message", "Unknown API error")
            raise RuntimeError(f"Sightengine error: {msg}")

        ai_prob = float(result["type"]["ai_generated"])
        label = "AI-Generated" if ai_prob >= CONFIDENCE_THRESHOLD else "Real"
        confidence = ai_prob if label == "AI-Generated" else 1.0 - ai_prob

        return {
            "label": label,
            "confidence": round(confidence, 4),
            "ai_probability": round(ai_prob, 4),
            "source": "Sightengine API",
        }


class DemoDetector:
    """
    Deterministic simulation — consistent results for the same image.
    Uses MD5 of image bytes as a seed so repeated uploads give the same answer.
    Clearly labelled as simulated in the UI.
    """

    def detect(self, image_bytes: bytes) -> dict:
        img_hash = hashlib.md5(image_bytes).hexdigest()
        seed = int(img_hash[:8], 16)
        rng = random.Random(seed)

        # Bias slightly toward AI-generated for demo interest
        ai_prob = rng.uniform(0.05, 0.98)
        label = "AI-Generated" if ai_prob >= CONFIDENCE_THRESHOLD else "Real"
        confidence = ai_prob if label == "AI-Generated" else 1.0 - ai_prob

        return {
            "label": label,
            "confidence": round(confidence, 4),
            "ai_probability": round(ai_prob, 4),
            "source": "Demo Mode (Simulated — no API key set)",
        }


def get_detector():
    """Return the appropriate detector based on config."""
    if DETECTION_MODE == "sightengine":
        return SightengineDetector()
    return DemoDetector()
