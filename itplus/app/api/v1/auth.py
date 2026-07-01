"""Auth endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from itplus.app.api.deps import get_current_user
from itplus.app.core.database import get_db
from itplus.app.core.security import create_access_token, verify_password
from itplus.app.models.user import User
from itplus.app.schemas.auth import LoginRequest, LoginResponse, UserResponse

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )
    token = create_access_token(subject=user.email, role=user.role)
    return LoginResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user
