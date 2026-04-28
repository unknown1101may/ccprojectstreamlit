"""
firebase_db.py — Firestore read/write for detection results.
Collection: "detections"
"""

from firebase_admin import firestore
from firebase_client import init_firebase


def save_result(result: dict) -> str:
    """
    Save a detection result document.
    Returns the new document ID.
    """
    init_firebase()
    db = firestore.client()
    _, doc_ref = db.collection("detections").add(result)
    return doc_ref.id


def get_all_results(limit: int = 50) -> list:
    """
    Fetch the most recent `limit` detection results, newest first.
    """
    init_firebase()
    db = firestore.client()

    docs = (
        db.collection("detections")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )

    results = []
    for doc in docs:
        data = doc.to_dict()
        data["doc_id"] = doc.id
        results.append(data)
    return results


def clear_all_results() -> None:
    """Delete all documents in the detections collection."""
    init_firebase()
    db = firestore.client()
    for doc in db.collection("detections").stream():
        doc.reference.delete()
