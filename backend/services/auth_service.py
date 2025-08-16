import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from supabase import create_client, Client
from config import get_settings

settings = get_settings()

class AuthService:
    def __init__(self):
        self.supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
        self.jwt_secret = settings.JWT_SECRET_KEY
        self.jwt_algorithm = settings.JWT_ALGORITHM
        self.jwt_expiration_hours = settings.JWT_EXPIRATION_HOURS
    
    def verify_supabase_jwt(self, token: str) -> Dict[str, Any]:
        """Verify Supabase JWT token"""
        try:
            # Use Supabase client to verify the token
            user = self.supabase.auth.get_user(token)
            if user and user.user:
                return {
                    "user_id": user.user.id,
                    "email": user.user.email,
                    "user_metadata": user.user.user_metadata
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token"
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
    
    def create_access_token(self, user_data: Dict[str, Any]) -> str:
        """Create JWT access token for API access"""
        expire = datetime.utcnow() + timedelta(hours=self.jwt_expiration_hours)
        to_encode = {
            "user_id": user_data["user_id"],
            "email": user_data["email"],
            "exp": expire,
            "iat": datetime.utcnow()
        }
        return jwt.encode(to_encode, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def verify_access_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT access token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            user_id: str = payload.get("user_id")
            email: str = payload.get("email")
            
            if user_id is None or email is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token"
                )
            
            return {
                "user_id": user_id,
                "email": email
            }
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
    
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile from Supabase"""
        try:
            response = self.supabase.table('profiles').select('*').eq('id', user_id).single().execute()
            return response.data if response.data else None
        except Exception:
            return None
    
    def create_user_profile(self, user_id: str, email: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create user profile in Supabase"""
        try:
            profile_data = {
                'id': user_id,
                'email': email,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if metadata:
                profile_data.update(metadata)
            
            response = self.supabase.table('profiles').insert(profile_data).execute()
            return response.data[0] if response.data else profile_data
        except Exception as e:
            # Profile might already exist, try to get it
            return self.get_user_profile(user_id) or profile_data