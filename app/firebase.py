import firebase_admin
from firebase_admin import credentials
import os
import json

firebase_app = None

def init_firebase():
    global firebase_app

    if firebase_app:
        return firebase_app

    try:
        # 🔥 OPTION 1: Railway ENV (BEST)
        firebase_key_json = os.getenv("FIREBASE_KEY")

        if firebase_key_json:
            print("🚀 Using Firebase ENV config")
            cred_dict = json.loads(firebase_key_json)
            cred = credentials.Certificate(cred_dict)

        else:
            # 🔥 OPTION 2: Local file fallback
            key_path = os.getenv("FIREBASE_KEY_PATH", "firebase_key.json")

            if not os.path.exists(key_path):
                raise FileNotFoundError(f"{key_path} not found")

            print("💻 Using local Firebase key file")
            cred = credentials.Certificate(key_path)

        firebase_app = firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized successfully")

    except Exception as e:
        print("❌ Firebase init error:", str(e))
        raise e

    return firebase_app