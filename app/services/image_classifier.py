import io
import json
import logging
import numpy as np
from PIL import Image
from fastapi import UploadFile, HTTPException
import os
import requests

import keras
from keras.applications import EfficientNetB0
from keras.applications.efficientnet import preprocess_input

# IMPORT CONFIG
try:
    from .config import settings
except ImportError:
    from config import settings

# LOGGER
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ImageClassifier")


class FoodClassifier:
    def __init__(self):
        self.indian_model = None
        self.modern_model = None
        self.imagenet_model = None
        self.indian_labels = []

        # 👇 Paths (local fallback)
        self.indian_model_path = settings.INDIAN_MODEL_PATH
        self.modern_model_path = settings.MODERN_MODEL_PATH
        self.labels_path = settings.INDIAN_LABELS_PATH

        # 👇 URLs (Railway)
        self.indian_model_url = os.getenv("INDIAN_MODEL_URL")
        self.modern_model_url = os.getenv("MODERN_MODEL_URL")
        self.labels_url = os.getenv("INDIAN_LABELS_URL")

        # Food101 labels
        self.food101_labels = [
            "apple_pie","baby_back_ribs","baklava","beef_carpaccio","beef_tartare","beet_salad","beignets",
            "bibimbap","bread_pudding","breakfast_burrito","bruschetta","caesar_salad","cannoli","caprese_salad",
            "carrot_cake","ceviche","cheesecake","cheese_plate","chicken_curry","chicken_quesadilla","chicken_wings",
            "chocolate_cake","chocolate_mousse","churros","clam_chowder","club_sandwich","crab_cakes","creme_brulee",
            "croque_madame","cup_cakes","deviled_eggs","donuts","dumplings","edamame","eggs_benedict","escargots",
            "falafel","filet_mignon","fish_and_chips","foie_gras","french_fries","french_onion_soup","french_toast",
            "fried_calamari","fried_rice","frozen_yogurt","garlic_bread","gnocchi","greek_salad","grilled_cheese_sandwich",
            "grilled_salmon","guacamole","gyoza","hamburger","hot_and_sour_soup","hot_dog","hummus","ice_cream",
            "lasagna","lobster_bisque","lobster_roll_sandwich","macaroni_and_cheese","macarons","miso_soup","mussels",
            "nachos","omelette","onion_rings","oysters","pad_thai","paella","pancakes","panna_cotta","peking_duck",
            "pho","pizza","pork_chop","poutine","prime_rib","pulled_pork_sandwich","ramen","ravioli","red_velvet_cake",
            "risotto","samosa","sashimi","scallops","seaweed_salad","shrimp_and_grits","spaghetti_bolognese",
            "spaghetti_carbonara","spring_rolls","steak","strawberry_shortcake","sushi","tacos","takoyaki","tiramisu",
            "tuna_tartare","waffles"
        ]

        self.load_models()

    # =========================
    # 📥 DOWNLOAD FILE (RAILWAY)
    # =========================
    def download_file(self, url, path):
        if not url:
            return

        import gdown

        os.makedirs(os.path.dirname(path), exist_ok=True)

        # ✅ Skip if already exists (safe for localhost)
        if os.path.exists(path) and os.path.getsize(path) > 1_000_000:
            logger.info(f"✅ File already exists: {path}")
            return

        logger.info(f"⬇️ Downloading from Google Drive: {url}")

        try:
            # 🔥 gdown handles everything automatically
            gdown.download(url, path, quiet=False)

        except Exception as e:
            logger.error(f"❌ Download failed: {str(e)}")
            raise RuntimeError("Download failed")

        # ✅ FINAL VALIDATION
        if not os.path.exists(path) or os.path.getsize(path) < 1000:
            raise RuntimeError("❌ Downloaded file is invalid or corrupted")

        logger.info(f"✅ Download successful: {path}")
    # =========================
    # 🚀 LOAD MODELS
    # =========================
    def load_models(self):
        try:
            logger.info("🔄 Loading Models...")

            # 🔥 Step 1: Download if running on Railway
            self.download_file(self.indian_model_url, self.indian_model_path)
            self.download_file(self.modern_model_url, self.modern_model_path)
            self.download_file(self.labels_url, self.labels_path)

            # 🔥 Step 2: Validate files
            if not os.path.exists(self.indian_model_path):
                raise FileNotFoundError(f"{self.indian_model_path} not found")

            if not os.path.exists(self.modern_model_path):
                raise FileNotFoundError(f"{self.modern_model_path} not found")

            if not os.path.exists(self.labels_path):
                raise FileNotFoundError(f"{self.labels_path} not found")

            # 🔥 Step 3: Load models
            self.indian_model = keras.models.load_model(self.indian_model_path)
            self.modern_model = keras.models.load_model(self.modern_model_path)
            self.imagenet_model = EfficientNetB0(weights="imagenet")

            with open(self.labels_path, "r") as f:
                self.indian_labels = json.load(f)

            logger.info("✅ Models Loaded Successfully")

        except Exception as e:
            logger.error(f"❌ Model Loading Failed: {str(e)}")
            raise RuntimeError("Model files not found or corrupted.")

    # =========================
    # 🧠 PREDICTION
    # =========================
    async def predict(self, uploaded_file: UploadFile) -> str:
        try:
            contents = await uploaded_file.read()
            image = Image.open(io.BytesIO(contents)).convert("RGB").resize((224, 224))
            img = np.expand_dims(np.array(image).astype("float32"), axis=0)
            img = preprocess_input(img)

            m_preds = self.modern_model.predict(img)[0]
            i_preds = self.indian_model.predict(img)[0]

            m_idx = np.argmax(m_preds)
            i_idx = np.argmax(i_preds)

            m_conf = float(m_preds[m_idx])
            i_conf = float(i_preds[i_idx])

            m_label = self.food101_labels[m_idx]
            i_label = self.indian_labels[i_idx]

            # 🔥 Smart Logic
            if "salad" in m_label.lower() and m_conf > 0.25:
                return m_label.replace("_", " ")

            if m_conf > 0.85:
                return m_label.replace("_", " ")

            if i_conf > m_conf + 0.15:
                return i_label.replace("_", " ")

            final = m_label if m_conf > i_conf else i_label
            return final.replace("_", " ")

        except Exception as e:
            logger.error(f"Inference error: {str(e)}")
            raise HTTPException(status_code=500, detail="Classification failed")


# GLOBAL INSTANCE
classifier = FoodClassifier()


async def classify_image(uploaded_file: UploadFile) -> str:
    return await classifier.predict(uploaded_file)