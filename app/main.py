from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine
from . import models
from .routes import auth, meals, goals, scan, profile, bmi
from app.routes import ai_chat
from app.routes import health
from app.routes.ai_assistant import router as ai_router
from app.routes import notifications
from app import firebase

import os

# =========================
# 🗄️ CREATE TABLES
# =========================
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="NutriVision API")

# =========================
# 🌍 CORS CONFIG (LOCAL + PROD)
# =========================
FRONTEND_URL = os.getenv("FRONTEND_URL")

origins = [
    "http://localhost:5173",  # Vite local
]

if FRONTEND_URL:
    origins.append(FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# 🚀 ROUTES
# =========================
app.include_router(auth.router)
app.include_router(meals.router)
app.include_router(goals.router)
app.include_router(scan.router)
app.include_router(profile.router)
app.include_router(bmi.router)
app.include_router(ai_chat.router)
app.include_router(health.router)
app.include_router(ai_router)
app.include_router(notifications.router)  # ✅ only once

# =========================
# 🏠 ROOT
# =========================
@app.get("/", tags=["Root"])
def root():
    return {"message": "NutriVision API is operational"}


# =========================
# 🚀 RUN (LOCAL + RAILWAY)
# =========================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)