from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.infrastructure.database.models import User
from app.core.security import hash_password, verify_password, create_access_token
from app.features.auth.schemas import UserRegisterRequest, UserLoginRequest, AuthTokenResponse, UserOut

def register_user(payload: UserRegisterRequest, db: Session) -> AuthTokenResponse:
    normalized_email = payload.email.strip().lower()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered.")

    user = User(
        email=normalized_email,
        password_hash=hash_password(payload.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut(id=user.id, email=user.email)
    )

def authenticate_user(payload: UserLoginRequest, db: Session) -> AuthTokenResponse:
    normalized_email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = create_access_token(user.id)
    return AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut(id=user.id, email=user.email)
    )
