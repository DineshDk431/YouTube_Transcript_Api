import json
import os

import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
load_dotenv()


def _init_firebase():
    """Initialize Firebase - supports both file-based and env-var-based credentials."""
    try:
        firebase_admin.get_app()
        return  # Already initialized
    except ValueError:
        pass

    # Option 1: JSON content from FIREBASE_CREDENTIALS_JSON env var
    cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
    if cred_json:
        try:
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase initialized from FIREBASE_CREDENTIALS_JSON env var")
            return
        except Exception as e:
            print(f"❌ Failed to parse FIREBASE_CREDENTIALS_JSON: {e}")

    # Option 2: FIREBASE_CREDENTIALS - could be JSON content OR a file path
    cred_val = os.getenv("FIREBASE_CREDENTIALS", "")
    if cred_val.strip().startswith("{"):
        # It's JSON content, not a file path
        try:
            cred_dict = json.loads(cred_val)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase initialized from FIREBASE_CREDENTIALS env var (JSON)")
            return
        except Exception as e:
            print(f"❌ Failed to parse FIREBASE_CREDENTIALS as JSON: {e}")

    # Option 3: File path (for local development)
    cred_path = cred_val if cred_val and not cred_val.strip().startswith("{") else "serviceAccountKey.json"
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        print(f"✅ Firebase initialized from file: {cred_path}")
    else:
        print("⚠️ Firebase credentials not found. Set FIREBASE_CREDENTIALS_JSON env var with your service account JSON.")


_init_firebase()


def get_db():
    try:
        return firestore.client()
    except Exception as e:
        print(f"❌ Error connecting to Firestore: {e}")
        return None
