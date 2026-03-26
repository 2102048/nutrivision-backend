from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    create_reset_token,
    verify_token,
    send_reset_email
)

router = APIRouter(prefix="/auth", tags=["Auth"])


# ✅ REGISTER
@router.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):

    existing_user = db.query(models.User).filter(
        models.User.email == user.email
    ).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = models.User(
        name=user.name,
        email=user.email,
        password=hash_password(user.password)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# ✅ LOGIN
@router.post("/login", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):

    user = db.query(models.User).filter(
        models.User.email == form_data.username
    ).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    if not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    access_token = create_access_token(
        data={"sub": user.email}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


# ✅ FORGOT PASSWORD
@router.post("/forgot-password")
def forgot_password(data: schemas.ForgotPassword, db: Session = Depends(get_db)):

    user = db.query(models.User).filter(
        models.User.email == data.email
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    reset_token = create_reset_token(user.email)

    send_reset_email(user.email, reset_token)

    return {"message": "Password reset email sent"}


# ✅ RESET PASSWORD
@router.post("/reset-password")
def reset_password(data: schemas.ResetPassword, db: Session = Depends(get_db)):

    payload = verify_token(data.token)

    if payload is None:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    email = payload.get("sub")

    user = db.query(models.User).filter(
        models.User.email == email
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password = hash_password(data.new_password)
    db.commit()

    return {"message": "Password reset successful"}