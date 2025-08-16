from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any, Optional
from services.auth_service import AuthService

security = HTTPBearer()
auth_service = AuthService()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user
    Requires valid JWT token in Authorization header
    """
    try:
        token = credentials.credentials
        user_data = auth_service.verify_access_token(token)
        return user_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Optional[Dict[str, Any]]:
    """
    Dependency to get current user if authenticated, None otherwise
    Does not raise error if no token provided
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        user_data = auth_service.verify_access_token(token)
        return user_data
    except Exception:
        return None