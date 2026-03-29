from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
import resend
import os

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User

# ===============================
# LOAD ENV VARIABLES
# ===============================

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


# ===============================
# PASSWORD HASHING
# ===============================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def hash_password(password: str) -> str:
    """
    Hash a plain password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


# ===============================
# AUTH TOKEN SYSTEM
# ===============================

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def create_access_token(data: dict) -> str:
    """
    Create login JWT token
    """
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(days=7)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return encoded_jwt


# ===============================
# PASSWORD RESET TOKEN
# ===============================

def create_reset_token(email: str) -> str:
    """
    Create short-lived password reset token
    """

    expire = datetime.utcnow() + timedelta(minutes=10)

    to_encode = {
        "sub": email,
        "exp": expire
    }

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def verify_token(token: str):
    """
    Verify JWT token and return payload
    """

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return payload

    except JWTError:

        return None


# ===============================
# SEND RESET EMAIL
# ===============================

def send_reset_email(to_email: str, reset_token: str):
    try:
        resend.api_key = os.getenv("RESEND_API_KEY")

        reset_link = f"{FRONTEND_URL}/reset-password/{reset_token}"

        response = resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": to_email,
            "subject": "NutriVision Password Reset",
            "html": f"""
                <h2>Reset Your Password</h2>
                <p>Click below:</p>
                <a href="{reset_link}">{reset_link}</a>
                <p>This link expires in 10 minutes.</p>
            """
        })

        print("✅ Email sent:", response)

    except Exception as e:
        print("❌ EMAIL ERROR:", str(e))
        raise Exception("Failed to send email")


# ===============================
# GET CURRENT LOGGED USER
# ===============================

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Extract logged-in user from JWT token
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        email: str = payload.get("sub")

        if email is None:
            raise credentials_exception

    except JWTError as e:
        print("JWT ERROR:", str(e))
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()

    if user is None:
        raise credentials_exception

    return user