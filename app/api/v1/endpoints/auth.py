import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends
import jwt

from app.schemas.auth import LoginRequest, LoginResponse, TokenRefreshRequest, UserInfo
from app.aws.cognito import cognito_client
from app.services.sponsor_manager import sponsor_service
from app.core.exceptions import AuthenticationError
from app.core.auth.utils import get_user_role
from app.middleware.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login", response_model=LoginResponse, summary="User Login")
async def login(credentials: LoginRequest):
    """
    Authenticate user with AWS Cognito and validate sponsor access.
    
    Process:
    1. Authenticate with AWS Cognito
    2. Extract user info from tokens
    3. Validate sponsor assignment (custom:sponsor claim)
    4. Validate user exists in sponsor's database (if sponsor assigned)
    5. Return tokens and user info
    """
    try:
        # Step 1: Authenticate with Cognito
        logger.info(f"Login attempt for user: {credentials.email}")
        auth_result = cognito_client.login(
            username=credentials.email,
            password=credentials.password
        )
        
        # Step 2: Decode ID token to get user claims (without verification, we already authenticated)
        id_token = auth_result['IdToken']
        decoded_token = jwt.decode(id_token, options={"verify_signature": False})
        
        # Step 3: Extract user information
        user_sub = decoded_token.get('sub')
        user_email = decoded_token.get('email')
        cognito_username = decoded_token.get('cognito:username')
        user_groups = decoded_token.get('cognito:groups', [])
        
        # Extract sponsor from custom attribute
        sponsor = decoded_token.get('custom:sponsor')
        
        if sponsor and (credentials.sponsor and credentials.sponsor != sponsor):
            logger.warning(f"Sponsor mismatch: token sponsor {sponsor}, request sponsor {credentials.sponsor} for user {user_email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sponsor mismatch between user and request"
            )
        
        user_role = decoded_token.get('custom:role', get_user_role(decoded_token))
        
        logger.info(f"User authenticated - email: {user_email}, sponsor: {sponsor}, role: {user_role}")
        
        # Step 4: Validate sponsor if assigned
        if sponsor:
            # Validate sponsor exists and is active
            sponsor_config = await sponsor_service.get_sponsor_config(sponsor)

            if not sponsor_config:
                logger.warning(f"Sponsor not found: {sponsor} for user {user_email}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Sponsor '{sponsor}' not found or inactive"
                )
            
            if not sponsor_config.get('is_active', False):
                logger.warning(f"Sponsor inactive: {sponsor} for user {user_email}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Sponsor '{sponsor}' is inactive"
                )
            
            # Step 5: Validate user in sponsor's database

            user_info = await sponsor_service.validate_user_in_sponsor_db(sponsor, user_email)
            if not user_info or user_info.get('status') != 1:
                logger.warning(f"User not found in sponsor {sponsor} database: {user_email}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"User '{user_email}' not found in sponsor '{sponsor}' database"
                )

            logger.info(f"User {user_email} validated for sponsor {sponsor}")
        else:
            user_info = await sponsor_service.validate_user_in_core_db(user_email)
            if not user_info or user_info.get('status') != 1:
                logger.warning(f"User not found in core database: {user_email}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"User '{user_email}' not found in core database"
                )
            logger.info(f"User {user_email} has no sponsor assigned (admin or global user)")
        
        # Step 6: Build user info response
        user_info = {
            "full_name": user_info['full_name'],
            "email": user_info['email'],
            "username": cognito_username or user_email,
            "sponsor": sponsor,
            "role": user_role,
            "groups": user_groups,
        }
        
        # Step 7: Return complete authentication response
        return LoginResponse(
            access_token=auth_result['AccessToken'],
            id_token=auth_result['IdToken'],
            refresh_token=auth_result['RefreshToken'],
            token_type=auth_result['TokenType'],
            expires_in=auth_result['ExpiresIn'],
            user_info=user_info
        )
        
    except AuthenticationError as e:
        logger.warning(f"Authentication failed for {credentials.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during login"
        )


@router.post("/token/refresh", response_model=Dict[str, Any], summary="Refresh Access Token")
async def refresh_token(request: TokenRefreshRequest):
    """
    Refresh access token using refresh token.
    
    Returns new access token and ID token.
    """
    try:
        logger.info("Token refresh attempt")
        
        # Refresh tokens with Cognito
        auth_result = cognito_client.login(None, None, request.refresh_token)
        
        logger.info("Token refreshed successfully")
        
        return {
            "access_token": auth_result['AccessToken'],
            "id_token": auth_result['IdToken'],
            "token_type": auth_result['TokenType'],
            "expires_in": auth_result['ExpiresIn'],
        }
        
    except AuthenticationError as e:
        logger.warning(f"Token refresh failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during token refresh: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during token refresh"
        )


@router.get("/me", response_model=UserInfo, summary="Get Current User Info")
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    
    Requires valid JWT token in Authorization header.
    Returns user information extracted from the JWT token claims.
    """
    try:
        # Extract sponsor from claims
        claims = current_user.get("claims", {})
        sponsor = current_user.get("sponsor")
        
        # Get user details from database
        if sponsor:
            user_db_info = await sponsor_service.validate_user_in_sponsor_db(sponsor, current_user["email"])
        else:
            user_db_info = await sponsor_service.validate_user_in_core_db(current_user["email"])
        print(f"user_db_info: {user_db_info}")
        # Build response with combined info from token and database
        return UserInfo(
            # sub=current_user["sub"],
            email=user_db_info["email"],
            sponsor=sponsor,
            role=current_user["role"],
            groups=current_user["groups"],
            username=current_user.get("username", current_user["email"]),
            email_verified=claims.get("email_verified", False),
            full_name=user_db_info.get("full_name") if user_db_info else None,
            user_id=user_db_info.get("user_id") if user_db_info else None,
        )
        
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user information"
        )
