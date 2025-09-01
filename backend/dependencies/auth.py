from fastapi import Depends, HTTPException, status, Query, Header
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
        user_data = auth_service.verify_supabase_jwt(token)
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
        user_data = auth_service.verify_supabase_jwt(token)
        return user_data
    except Exception:
        return None

async def get_user_from_token_param(token: Optional[str] = Query(None), authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    """
    Dependency to get current user from token query parameter or Authorization header (Bearer)
    Used for SSE connections where custom headers are hard to set from browsers.
    """
    # Attempt to extract token from Authorization header if not provided as query param
    if not token and authorization:
        try:
            if authorization.startswith("Bearer "):
                token = authorization.split(" ", 1)[1].strip()
        except Exception:
            token = None

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token parameter required for SSE authentication",
        )
    
    # Debug (masked) - avoid logging sensitive data
    try:
        masked = token[:8] + "..." if len(token) > 8 else "(short token)"
        print(f"[AUTH] Verifying token (masked): {masked}")
    except Exception:
        pass

    try:
        user_data = auth_service.verify_supabase_jwt(token)
        print(f"[AUTH] Token verified for user: {user_data.get('user_id')}")
        return user_data
    except HTTPException:
        print("[AUTH] Token verification failed with HTTPException")
        raise
    except Exception as e:
        print(f"[AUTH] Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate token parameter",
        )