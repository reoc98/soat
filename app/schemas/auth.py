from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any


class LoginRequest(BaseModel):
    """Login request schema."""
    
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="User password")
    sponsor: Optional[str] = Field(None, description="Sponsor ID")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "fabian@red5g.com",
                "password": "tempralPass123"
            }
        }


class LoginResponse(BaseModel):
    """Login response schema."""
    
    access_token: str = Field(..., description="JWT access token")
    id_token: str = Field(..., description="JWT ID token")
    refresh_token: str = Field(..., description="Refresh token for token renewal")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user_info: Dict[str, Any] = Field(..., description="User information")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJraWQiOiJ...",
                "id_token": "eyJraWQiOiJ...",
                "refresh_token": "eyJjdHkiOiJ...",
                "token_type": "Bearer",
                "expires_in": 3600,
                "user_info": {
                    "full_name": "John Doe",
                    "email": "user@example.com",
                    "username": "johndoe",
                    "sponsor": "rappi",
                    "role": "sponsor",
                    "groups": ["sponsor"],
                }
            }
        }


class TokenRefreshRequest(BaseModel):
    """Token refresh request schema."""
    
    refresh_token: str = Field(..., description="Refresh token")

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJjdHkiOiJ..."
            }
        }


class UserInfo(BaseModel):
    """User information schema."""
    
    # sub: str = Field(..., description="User unique identifier (Cognito sub)")
    email: EmailStr = Field(..., description="User email")
    sponsor: Optional[str] = Field(None, description="Sponsor/tenant identifier")
    role: str = Field(..., description="User role")
    groups: List[str] = Field(default_factory=list, description="User groups")
    username: Optional[str] = Field(None, description="Username")
    email_verified: bool = Field(default=False, description="Email verification status")
    full_name: Optional[str] = Field(None, description="Full name of the user")
    user_id: Optional[int] = Field(None, description="Database user ID")

    class Config:
        json_schema_extra = {
            "example": {
                # "sub": "uuid-user-id",
                "email": "user@example.com",
                "sponsor": "rappi",
                "role": "sponsor",
                "groups": ["sponsor"],
                "username": "user@example.com",
                "email_verified": True,
                "full_name": "John Doe",
                "user_id": 123
            }
        }
