from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Dict, Any
from services.auth_service import AuthService
from dependencies.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["authentication"])
auth_service = AuthService()

class TokenRequest(BaseModel):
    token: str

class UserResponse(BaseModel):
    user_id: str
    email: str
    profile: Dict[str, Any] | None = None

@router.post("/verify", response_model=Dict[str, Any])
async def verify_token(request: TokenRequest):
    """Verify Supabase JWT token and return user info"""
    try:
        user_data = auth_service.verify_supabase_jwt(request.token)
        
        # Get or create user profile
        profile = auth_service.get_user_profile(user_data["user_id"])
        if not profile:
            profile = auth_service.create_user_profile(
                user_data["user_id"],
                user_data["email"],
                user_data.get("user_metadata", {})
            )
        
        # Create API access token
        access_token = auth_service.create_access_token(user_data)
        
        return {
            "status": "success",
            "user": {
                "user_id": user_data["user_id"],
                "email": user_data["email"],
                "profile": profile
            },
            "access_token": access_token
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication verification failed"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current authenticated user information"""
    profile = auth_service.get_user_profile(current_user["user_id"])
    
    return UserResponse(
        user_id=current_user["user_id"],
        email=current_user["email"],
        profile=profile
    )

@router.post("/refresh")
async def refresh_token(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Refresh API access token"""
    access_token = auth_service.create_access_token(current_user)
    
    return {
        "status": "success",
        "access_token": access_token
    }