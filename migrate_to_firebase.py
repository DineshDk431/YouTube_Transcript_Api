import json
import firebase_admin
from firebase_admin import credentials, firestore
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

cred_path = os.getenv("FIREBASE_CREDENTIALS", "serviceAccountKey.json")
if not os.path.exists(cred_path):
    print(f"❌ Error: Credentials not found at {cred_path}")
    exit(1)

cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)
db = firestore.client()

USERS_FILE = Path("users.json")
HISTORY_DIR = Path("data/history")

def migrate_users():
    if not USERS_FILE.exists():
        print("⚠️ No users.json found.")
        return

    print("🚀 Migrating Users...")
    with open(USERS_FILE, "r") as f:
        users = json.load(f)

    batch = db.batch()
    count = 0
    for email, data in users.items():
        doc_ref = db.collection("users").document(email)
        batch.set(doc_ref, data, merge=True)
        count += 1
        if count % 400 == 0:
            batch.commit()
            batch = db.batch()
            print(f"   ...committed {count} users")
    
    batch.commit()
    print(f"✅ Migrated {count} users.")

def migrate_history():
    if not HISTORY_DIR.exists():
        print("⚠️ No history directory found.")
        return

    print("🚀 Migrating History...")
    user_files = list(HISTORY_DIR.glob("*.json"))
    
    total_notes = 0
    for file_path in user_files:
        filename = file_path.stem
        email = filename.replace("_at_", "@")
        
        print(f"   Processing {email}...")
        try:
            history_list = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}")
            continue

        if not history_list:
            continue

        batch = db.batch()
        batch_count = 0
        
        history_col = db.collection("users").document(email).collection("history")
        
        for note in history_list:

            note_id = note.get("id")
            if not note_id:
                continue
                
            doc_ref = history_col.document(note_id)
            batch.set(doc_ref, note)
            batch_count += 1
            total_notes += 1
            
            if batch_count >= 400:
                batch.commit()
                batch = db.batch()
                batch_count = 0
        
        batch.commit()

    print(f"✅ Migrated {total_notes} history items across {len(user_files)} users.")

if __name__ == "__main__":
    confirm = input("This will upload data to Firestore. Ensure serviceAccountKey.json is correct. Proceed? (y/n): ")
    if confirm.lower() == 'y':
        migrate_users()
        migrate_history()
        print("\n✨ Migration Complete!")
