from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.all_models import User
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, UserOut
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)

class AuthService:
    @staticmethod
    def register_user(db: Session, user_in: UserRegister) -> UserOut:
        existing_user = db.query(User).filter(User.email == user_in.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists."
            )
        hashed_pwd = get_password_hash(user_in.password)
        db_user = User(
            email=user_in.email,
            hashed_password=hashed_pwd,
            full_name=user_in.full_name,
            role=user_in.role or "OPERATIONS_LEAD"
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return UserOut.model_validate(db_user)

    @staticmethod
    def authenticate_user(db: Session, credentials: UserLogin) -> TokenResponse:
        user = db.query(User).filter(User.email == credentials.email).first()
        if not user or not verify_password(credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password."
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive."
            )
        access_token = create_access_token(subject=user.email)
        refresh_token = create_refresh_token(subject=user.email)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token
        )

    @staticmethod
    def refresh_access_token(token: str) -> TokenResponse:
        payload = decode_token(token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token."
            )
        email = payload.get("sub")
        new_access_token = create_access_token(subject=email)
        new_refresh_token = create_refresh_token(subject=email)
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token
        )
