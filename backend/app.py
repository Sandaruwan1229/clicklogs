"""
Tap experiment backend — Flask app hosted on Render (free tier).

Receives POST data from the frontend and saves each tap record
to Firebase Firestore collection 'tap_logs'.
"""

import json
import os
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


@app.route("/saveTaps", methods=["POST"])
def save_taps():
    """
    Receives form-encoded POST body:
        id   = session identifier
        var  = device platform ('android' or 'pc')
        taps = JSON array of tap objects
    """
    try:
        # a. Tap sequence number  b. timestamps  c. interface  d. session  e. platform
        session_id      = request.form.get("id",   "unknown")
        device_platform = request.form.get("var",  "unknown")
        taps_raw        = request.form.get("taps", "[]")

        taps_list = json.loads(taps_raw)

        batch = db.batch()

        for tap in taps_list:
            start_ts = tap.get("startTimestamp", 0)
            end_ts   = tap.get("endTimestamp",   0)

            record = {
                # a. Tap sequence number
                "tapSequenceNumber": tap.get("tapSequenceNumber"),
                # b. Start / end timestamps (ms since Unix epoch)
                "startTimestamp":    start_ts,
                "endTimestamp":      end_ts,
                # Derived: duration stored for easy querying
                "tapDuration":       end_ts - start_ts,
                # c. Interface type
                "interface":         tap.get("interface"),        # 'feedbackshown' or 'nofeedback'
                "interfaceSequence": tap.get("interfaceSequence"),
                # d. Session identifier
                "sessionId":         session_id,
                # e. Device platform
                "devicePlatform":    device_platform,             # 'android' or 'pc'
            }

            doc_ref = db.collection("tap_logs").document()
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
