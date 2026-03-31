"""
Tap experiment backend — Flask app hosted on Render (free tier).

Receives POST data from the frontend and saves each tap record
to Firebase Firestore collection 'tap_logs'.

Document ID format : {sessionId}_{tapNumber}  e.g. "abc123_1"
"""

import json
import os
from datetime import datetime, timezone
from flask import Flask, request
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)
CORS(app)  # Allow requests from GitHub Pages (any origin)

# ---------------------------------------------------------------------------
# Firebase initialisation
# The full service account JSON is stored as a Render environment variable
# called FIREBASE_SERVICE_ACCOUNT.
# ---------------------------------------------------------------------------
service_account_info = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT"])
cred = credentials.Certificate(service_account_info)
firebase_admin.initialize_app(cred)
db = firestore.client()


def ms_to_datetime(ms):
    """Convert a JavaScript millisecond timestamp to a UTC datetime."""
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)


@app.route("/saveTaps", methods=["POST"])
def save_taps():
    """
    Receives form-encoded POST body:
        id   = session identifier
        var  = device platform ('android' or 'pc')
        taps = JSON array of tap objects
    """
    try:
        session_id      = request.form.get("id",   "unknown")
        device_platform = request.form.get("var",  "unknown")
        taps_raw        = request.form.get("taps", "[]")

        taps_list = json.loads(taps_raw)

        # Normalise devicePlatform to "Android" or "PC"
        platform_map = {"android": "Android", "pc": "PC"}
        device_platform = platform_map.get(device_platform.lower(), device_platform.capitalize())

        batch = db.batch()

        for tap in taps_list:
            start_ms = tap.get("startTimestamp", 0)
            end_ms   = tap.get("endTimestamp",   0)
            tap_num  = tap.get("tapSequenceNumber", 0)

            # Map "feedbackshown" → "feedback", keep "nofeedback" as-is
            raw_interface = tap.get("interface", "")
            interface_type = "feedback" if raw_interface == "feedbackshown" else "nofeedback"

            # Document ID: {sessionId}_{tapNumber}
            # doc_id  = f"{session_id}_{tap_num}"
            doc_ref = db.collection("tap_logs").document()

            record = {
                "sessionId":       session_id,
                "tapNumber":       tap_num,
                "startTimestamp":  ms_to_datetime(start_ms),   # stored as Firestore Timestamp
                "endTimestamp":    ms_to_datetime(end_ms),      # stored as Firestore Timestamp
                "duration":        end_ms - start_ms,           # ms
                "interfaceType":   interface_type,              # "feedback" or "nofeedback"
                "devicePlatform":  device_platform,             # "Android" or "PC"
                "serverTimestamp": firestore.SERVER_TIMESTAMP,  # time of save on server
            }

            batch.set(doc_ref, record)

        batch.commit()
        return "Data saved successfully", 200

    except Exception as e:
        print(f"Error: {e}")
        return f"Error: {str(e)}", 500


@app.route("/", methods=["GET"])
def health():
    return "Tap backend is running.", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
