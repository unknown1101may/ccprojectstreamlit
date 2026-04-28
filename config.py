import os

# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------
CONFIDENCE_THRESHOLD = 0.7

SIGHTENGINE_API_USER   = os.getenv("SIGHTENGINE_API_USER", "")
SIGHTENGINE_API_SECRET = os.getenv("SIGHTENGINE_API_SECRET", "")

# ---------------------------------------------------------------------------
# Firebase
# ---------------------------------------------------------------------------
# Path to your Firebase service-account JSON file, OR the raw JSON string
FIREBASE_SERVICE_ACCOUNT = os.getenv("FIREBASE_SERVICE_ACCOUNT", "")

# Your Firebase Storage bucket, e.g. "my-project.appspot.com"
FIREBASE_STORAGE_BUCKET  = os.getenv("FIREBASE_STORAGE_BUCKET", "")

# URL of the deployed Cloud Function (HTTP trigger)
# e.g. "https://us-central1-my-project.cloudfunctions.net/detect_image"
CLOUD_FUNCTION_URL = os.getenv("CLOUD_FUNCTION_URL", "")

# True when Firebase credentials are present
FIREBASE_ENABLED = bool(FIREBASE_SERVICE_ACCOUNT and FIREBASE_STORAGE_BUCKET)

# ---------------------------------------------------------------------------
# Detection mode
# ---------------------------------------------------------------------------
DETECTION_MODE = (
    "sightengine"
    if SIGHTENGINE_API_USER and SIGHTENGINE_API_SECRET
    else "demo"
)
