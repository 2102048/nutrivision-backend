from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth_utils import verify_token

router = APIRouter(prefix="/health", tags=["Health"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ✅ GET CURRENT USER
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):

    payload = verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    email = payload.get("sub")

    user = db.query(models.User).filter(
        models.User.email == email
    ).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user


# ✅ UPDATE HEALTH DATA
@router.post("/update")
def update_health(
    data: schemas.UpdateHealth,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    bmi = data.weight / ((data.height / 100) ** 2)

    record = models.BMIRecord(
        user_id=current_user.id,
        age=data.age,
        gender=data.gender,
        height=data.height,
        weight=data.weight,
        bmi=bmi
    )

    db.add(record)
    db.commit()

    return {
        "message": "Health data updated",
        "bmi": round(bmi, 2)
    }