import io
import json
import logging
import numpy as np
from PIL import Image
from fastapi import UploadFile, HTTPException

import keras
from keras.applications import EfficientNetB0
from keras.applications.efficientnet import preprocess_input, decode_predictions

# IMPORT CONFIGURATION
try:
    from .config import settings
except ImportError:
    # Fallback for direct script execution
    from config import settings

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ImageClassifier")

class FoodClassifier:
    def __init__(self):
        self.indian_model = None
        self.modern_model = None
        self.imagenet_model = None
        self.indian_labels = []
        
        # Standard Food101 Categories
        self.food101_labels = [
            "apple_pie", "baby_back_ribs", "baklava", "beef_carpaccio", "beef_tartare", "beet_salad", "beignets", 
            "bibimbap", "bread_pudding", "breakfast_burrito", "bruschetta", "caesar_salad", "cannoli", "caprese_salad", 
            "carrot_cake", "ceviche", "cheesecake", "cheese_plate", "chicken_curry", "chicken_quesadilla", "chicken_wings", 
            "chocolate_cake", "chocolate_mousse", "churros", "clam_chowder", "club_sandwich", "crab_cakes", "creme_brulee", 
            "croque_madame", "cup_cakes", "deviled_eggs", "donuts", "dumplings", "edamame", "eggs_benedict", "escargots", 
            "falafel", "filet_mignon", "fish_and_chips", "foie_gras", "french_fries", "french_onion_soup", "french_toast", 
            "fried_calamari", "fried_rice", "frozen_yogurt", "garlic_bread", "gnocchi", "greek_salad", "grilled_cheese_sandwich", 
            "grilled_salmon", "guacamole", "gyoza", "hamburger", "hot_and_sour_soup", "hot_dog", "hummus", "ice_cream", 
            "lasagna", "lobster_bisque", "lobster_roll_sandwich", "macaroni_and_cheese", "macarons", "miso_soup", "mussels", 
            "nachos", "omelette", "onion_rings", "oysters", "pad_thai", "paella", "pancakes", "panna_cotta", "peking_duck", 
            "pho", "pizza", "pork_chop", "poutine", "prime_rib", "pulled_pork_sandwich", "ramen", "ravioli", "red_velvet_cake", 
            "risotto", "samosa", "sashimi", "scallops", "seaweed_salad", "shrimp_and_grits", "spaghetti_bolognese", 
            "spaghetti_carbonara", "spring_rolls", "steak", "strawberry_shortcake", "sushi", "tacos", "takoyaki", "tiramisu", 
            "tuna_tartare", "waffles"
        ]
        
        self.fruit_ids = {
            "n07753592": "banana", "n07742313": "apple", "n07747607": "orange",
            "n07753275": "pineapple", "n07768694": "pomegranate", 
            "n07745940": "strawberry", "n07749582": "lemon",
        }
        self.load_models()

    def load_models(self):
        try:
            logger.info("🔄 Loading Neural Networks...")
            self.indian_model = keras.models.load_model(settings.INDIAN_MODEL_PATH)
            self.modern_model = keras.models.load_model(settings.MODERN_MODEL_PATH)
            self.imagenet_model = EfficientNetB0(weights="imagenet")
            
            with open(settings.INDIAN_LABELS_PATH, "r") as f:
                self.indian_labels = json.load(f)
            logger.info("✅ High-scale model deployment active.")
        except Exception as e:
            logger.error(f"❌ Initialization Error: {str(e)}")
            raise RuntimeError("Model files not found or corrupted.")

    async def predict(self, uploaded_file: UploadFile) -> str:
        try:
            contents = await uploaded_file.read()
            image = Image.open(io.BytesIO(contents)).convert("RGB").resize((224, 224))
            img_batch = preprocess_input(np.expand_dims(np.array(image).astype("float32"), axis=0))

            # --- 1. RUN INFERENCE ---
            m_preds = self.modern_model.predict(img_batch)[0]
            i_preds = self.indian_model.predict(img_batch)[0]

            m_idx = np.argmax(m_preds)
            m_conf, m_label = float(m_preds[m_idx]), self.food101_labels[m_idx]

            i_idx = np.argmax(i_preds)
            i_conf, i_label = float(i_preds[i_idx]), self.indian_labels[i_idx]

            # --- 2. THE ARBITRATION BRAIN (The Fix) ---
            
            # SALAD OVERRIDE: 
            # If Food101 detects ANY type of salad, we prioritize it.
            # Indian models often confuse 'leafy salads' with 'rice' or 'saag'.
            if "salad" in m_label.lower() and m_conf > 0.25:
                logger.info(f"🥗 Salad heuristic triggered: {m_label} ({m_conf:.2f})")
                return m_label.replace("_", " ")

            # HIGH CONFIDENCE GLOBAL MATCH
            # If the modern model is very sure (>85%), it's likely a global dish.
            if m_conf > 0.85:
                logger.info(f"🍔 Global Model dominant: {m_label}")
                return m_label.replace("_", " ")

            # INDIAN SPECIALTY MATCH
            # Only use Indian label if it's much more confident than the global one
            if i_conf > m_conf + 0.15:
                logger.info(f" Curry Indian Model dominant: {i_label}")
                return i_label.replace("_", " ")

            # FINAL FALLBACK
            final_result = m_label if m_conf > i_conf else i_label
            return final_result.replace("_", " ")

        except Exception as e:
            logger.error(f"Inference error: {str(e)}")
            raise HTTPException(status_code=500, detail="Classification failed")
# Global instance for the FastAPI app
classifier = FoodClassifier()

async def classify_image(uploaded_file: UploadFile) -> str:
    return await classifier.predict(uploaded_file)