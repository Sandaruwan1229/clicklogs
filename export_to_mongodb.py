"""
Export tap_logs from Firebase Firestore to MongoDB Atlas.

Run this locally AFTER collecting data:
    pip install firebase-admin pymongo
    python export_to_mongodb.py

You need:
  - serviceAccount.json  (downloaded from Firebase console)
  - Your MongoDB Atlas connection string
"""

import firebase_admin
from firebase_admin import credentials, firestore
from pymongo import MongoClient

# --- CONFIG: Fill these in ---
FIREBASE_SERVICE_ACCOUNT = "serviceAccount.json"
MONGODB_CONNECTION_STRING = "mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/"
MONGODB_DATABASE = "clicklogs"
MONGODB_COLLECTION = "tap_logs"
# -----------------------------


def export():
    # Connect to Firestore
    cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT)
    firebase_admin.initialize_app(cred)
    fs = firestore.client()

    # Connect to MongoDB Atlas
    mongo_client = MongoClient(MONGODB_CONNECTION_STRING)
    mongo_col = mongo_client[MONGODB_DATABASE][MONGODB_COLLECTION]

    # Fetch all tap_logs from Firestore
    docs = fs.collection("tap_logs").stream()

    count = 0
    for doc in docs:
        data = doc.to_dict()
        data["_id"] = doc.id  # use Firestore doc ID as MongoDB _id
        # Upsert so re-running doesn't create duplicates
        mongo_col.replace_one({"_id": data["_id"]}, data, upsert=True)
        count += 1

    print(f"Exported {count} records to MongoDB Atlas collection '{MONGODB_COLLECTION}'")
    mongo_client.close()


if __name__ == "__main__":
    export()
