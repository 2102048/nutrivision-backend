import firebase_admin
from firebase_admin import credentials
import os

key_path = os.getenv("FIREBASE_KEY_PATH", "firebase_key.json")

cred = credentials.Certificate(key_path)

firebase_admin.initialize_app(cred)