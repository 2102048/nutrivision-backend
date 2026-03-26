# Create a config.py or keep this at the top of your service
import os
from dotenv import load_dotenv
load_dotenv()

class Settings:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ML_DIR = os.path.join(BASE_DIR, "ml")
    
    INDIAN_MODEL_PATH = os.path.join(ML_DIR, "indian_food_model.keras")
    MODERN_MODEL_PATH = os.path.join(ML_DIR, "food101_modern.keras")
    INDIAN_LABELS_PATH = os.path.join(ML_DIR, "class_names.json")
    
    # Thresholds for decision logic
    GLOBAL_CONFIDENCE_THRESHOLD = 0.80
    INDIAN_CONFIDENCE_THRESHOLD = 0.75
    MIN_ACCEPTABLE_CONFIDENCE = 0.30

settings = Settings()