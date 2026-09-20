from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.common import APIResponse
from app.schemas.auth import UserRegister, UserLogin, RefreshTokenRequest, TokenResponse, UserOut
from app.services.auth_service import AuthService
from app.api.deps import get_current_user
from app.models.all_models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=APIResponse[UserOut], status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    user_out = AuthService.register_user(db, user_in)
    return APIResponse(
        success=True,
        message="User account registered successfully.",
        data=user_out
    )

@router.post("/login", response_model=APIResponse[TokenResponse])
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    tokens = AuthService.authenticate_user(db, credentials)
    return APIResponse(
        success=True,
        message="Login successful.",
        data=tokens
    )

@router.post("/refresh", response_model=APIResponse[TokenResponse])
def refresh_token(req: RefreshTokenRequest):
    tokens = AuthService.refresh_access_token(req.refresh_token)
    return APIResponse(
        success=True,
        message="Access token refreshed successfully.",
        data=tokens
    )

@router.post("/logout", response_model=APIResponse[dict])
def logout(current_user: User = Depends(get_current_user)):
    return APIResponse(
        success=True,
        message="Logged out successfully.",
        data={"user": current_user.email}
    )

@router.get("/me", response_model=APIResponse[UserOut])
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return APIResponse(
        success=True,
        message="Current user profile retrieved successfully.",
        data=UserOut.model_validate(current_user)
    )
