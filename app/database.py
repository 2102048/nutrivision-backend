from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

load_dotenv()

# =========================
# 📦 DATABASE URL
# =========================
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL is not set in environment variables")

# =========================
# 🧠 ENV DETECTION
# =========================
# Railway / Neon → PostgreSQL with SSL
# Local → SQLite or local Postgres (no SSL)

is_postgres = DATABASE_URL.startswith("postgresql")

# =========================
# 🚀 ENGINE CREATION
# =========================
if is_postgres:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        connect_args={"sslmode": "require"}  # ✅ needed for Railway/Neon
    )
else:
    # Local DB (SQLite or non-SSL Postgres)
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True
    )

# =========================
# 🧩 SESSION
# =========================
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# =========================
# 🧱 BASE
# =========================
Base = declarative_base()

# =========================
# 🔄 DB DEPENDENCY
# =========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()