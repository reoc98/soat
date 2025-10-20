import logging
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError
import json
from os import getenv

from app.core.config import settings
from app.core.exceptions import AuthenticationError

logger = logging.getLogger(__name__)

class AWSCognitoClient:
    """AWS Cognito client for user management and authentication."""

    def __init__(self):
        self._client = None
        self.client_id = getenv("COGNITO_APP_CLIENT_ID")
        self.user_pool_id = getenv("COGNITO_USER_POOL_ID") 


    def _get_client(self):
        """Get or create boto3 Cognito client."""
        if self._client is None:
            self._client = boto3.client(
                'cognito-idp',
                region_name=getenv("AWS_REGION"),
            )
        return self._client

    def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from access token."""
        try:
            client = self._get_client()
            response = client.get_user(AccessToken=access_token)
            return {
                'username': response['Username'],
                'attributes': {attr['Name']: attr['Value'] for attr in response['UserAttributes']},
                'groups': []  # Would need admin_get_user or similar for groups
            }
        except ClientError as e:
            logger.error(f"Error getting user info: {e}")
            return None

    def create_user(self, username: str, email: str, sponsor_id: str) -> bool:
        """Create a new user in Cognito User Pool."""
        try:
            client = self._get_client()
            client.admin_create_user(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                Username=username,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'email_verified', 'Value': 'true'},
                    {'Name': 'custom:sponsor', 'Value': sponsor_id}
                ],
                MessageAction='SUPPRESS'  # Don't send welcome email
            )
            return True
        except ClientError as e:
            logger.error(f"Error creating user {username}: {e}")
            return False

    def authenticate(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user with AWS Cognito using ADMIN_USER_PASSWORD_AUTH flow.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Dictionary with authentication result including tokens
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            client = self._get_client()
            
            # Use ADMIN_USER_PASSWORD_AUTH for server-side authentication
            response = client.admin_initiate_auth(
                UserPoolId=self.user_pool_id,
                ClientId=self.client_id,
                AuthFlow='ADMIN_USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': email,
                    'PASSWORD': password,
                }
            )
            
            # Extract authentication result
            auth_result = response.get('AuthenticationResult')
            if not auth_result:
                raise AuthenticationError("Authentication failed: No authentication result")
            
            logger.info(f"User authenticated successfully: {email}")
            
            return {
                'access_token': auth_result.get('AccessToken'),
                'id_token': auth_result.get('IdToken'),
                'refresh_token': auth_result.get('RefreshToken'),
                'token_type': auth_result.get('TokenType', 'Bearer'),
                'expires_in': auth_result.get('ExpiresIn', 3600),
            }
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            logger.warning(f"Cognito authentication failed for {email}: {error_code} - {error_message}")
            
            if error_code == 'NotAuthorizedException':
                raise AuthenticationError("Invalid email or password")
            elif error_code == 'UserNotFoundException':
                raise AuthenticationError("Invalid email or password") # User not found
            elif error_code == 'UserNotConfirmedException':
                raise AuthenticationError("Invalid email or password") # User not confirmed
            elif error_code == 'PasswordResetRequiredException':
                raise AuthenticationError("Password reset required")
            elif error_code == 'TooManyRequestsException':
                raise AuthenticationError("Too many login attempts. Please try again later")
            else:
                raise AuthenticationError(f"Authentication failed: {error_message}")
                
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {str(e)}", exc_info=True)
            raise AuthenticationError(f"Authentication service error: {str(e)}")

    def get_user_attributes(self, access_token: str) -> Dict[str, Any]:
        """
        Get user attributes from Cognito using access token.
        
        Args:
            access_token: User's access token
            
        Returns:
            Dictionary with user attributes
        """
        try:
            client = self._get_client()
            
            response = client.get_user(
                AccessToken=access_token
            )
            
            # Parse attributes
            attributes = {}
            for attr in response.get('UserAttributes', []):
                attributes[attr['Name']] = attr['Value']
            
            return {
                'username': response.get('Username'),
                'attributes': attributes,
                'user_status': response.get('UserStatus'),
            }
            
        except ClientError as e:
            logger.error(f"Failed to get user attributes: {str(e)}")
            raise AuthenticationError("Failed to retrieve user information")

    def refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: User's refresh token
            
        Returns:
            Dictionary with new tokens
        """
        try:
            client = self._get_client()
            
            response = client.admin_initiate_auth(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                ClientId=settings.COGNITO_APP_CLIENT_ID,
                AuthFlow='REFRESH_TOKEN_AUTH',
                AuthParameters={
                    'REFRESH_TOKEN': refresh_token,
                }
            )
            
            auth_result = response.get('AuthenticationResult')
            if not auth_result:
                raise AuthenticationError("Token refresh failed")
            
            return {
                'access_token': auth_result.get('AccessToken'),
                'id_token': auth_result.get('IdToken'),
                'token_type': auth_result.get('TokenType', 'Bearer'),
                'expires_in': auth_result.get('ExpiresIn', 3600),
            }
            
        except ClientError as e:
            logger.error(f"Token refresh failed: {str(e)}")
            raise AuthenticationError("Invalid or expired refresh token")
    
    def login(self, username: str, password: str, refresh_token: str = ""):
        """
        Login de usuario
        param: email
            email del usuario
        param: password
            password del usuario
        return: response
            respuesta de cognito
        """
        print("Login called with:", username, "Refresh token present:", bool(refresh_token))
        print("Client ID:", self.client_id, "User Pool ID:", self.user_pool_id)
        if refresh_token:
            flow_type = "REFRESH_TOKEN"
            auth_params = {
                "REFRESH_TOKEN": refresh_token
            }
        else:
            flow_type = "USER_PASSWORD_AUTH"
            auth_params = {
                "USERNAME": username,
                "PASSWORD": password
            }
        tokens = self.__get_tokens(flow_type, auth_params)
        
        return tokens

    def __get_tokens(self, auth_flow: str, auth_params: dict):
        """
        Obtener tokens de autenticación
        :param auth_flow: 
            Tipo de flujo de autenticación
        :param auth_params: 
            Parámetros de autenticación
        :return: 
            Tokens de autenticación
        """
        try:
            response = self._get_client().initiate_auth(
                ClientId=self.client_id,
                AuthFlow=auth_flow,
                AuthParameters=auth_params
            )
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            error_message = e.response.get('Error', {}).get('Message', str(e))

            logger.warning(f"Cognito authentication failed for {auth_params['USERNAME']}: {error_code} - {error_message}")

            if error_code == 'NotAuthorizedException':
                raise AuthenticationError("Invalid email or password")
            elif error_code == 'UserNotFoundException':
                raise AuthenticationError("Invalid email or password") # User not found
            elif error_code == 'UserNotConfirmedException':
                raise AuthenticationError("Invalid email or password") # User email not confirmed
            elif error_code == 'PasswordResetRequiredException':
                raise AuthenticationError("Invalid email or password") # Password reset required
            elif error_code == 'TooManyRequestsException':
                raise AuthenticationError("Too many login attempts. Please try again later")
            else:
                raise AuthenticationError(f"Authentication failed: {error_message}")

        tokens_result = response["AuthenticationResult"]

        tokens = {}
        # print(tokens_result)
        tokens["AccessToken"] = tokens_result["AccessToken"]
        tokens["IdToken"] = tokens_result["IdToken"]
        tokens["ExpiresIn"] = tokens_result["ExpiresIn"]
        tokens["TokenType"] = tokens_result["TokenType"]

        if auth_flow == "USER_PASSWORD_AUTH":
            tokens["RefreshToken"] = tokens_result["RefreshToken"]

        return tokens
# Global instance
cognito_client = AWSCognitoClient()