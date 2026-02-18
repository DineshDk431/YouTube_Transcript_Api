import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
load_dotenv()

cred_path = os.getenv("FIREBASE_CREDENTIALS", "serviceAccountKey.json")

if not os.path.exists(cred_path):
    print(f"⚠️ Warning: Firebase credentials not found at {cred_path}")
    try:
        firebase_admin.get_app()
    except ValueError:
        pass 
else:
    cred = credentials.Certificate(cred_path)
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(cred)

def get_db():
    try:
        return firestore.client()
    except Exception as e:
        print(f"❌ Error connecting to Firestore: {e}")
        return None
