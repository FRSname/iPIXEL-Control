"""
Microsoft Teams/Graph API Client for iPIXEL Controller
"""

import requests
import urllib.parse
from typing import Dict, Any, Optional
from utils.logger import get_logger

logger = get_logger()


class TeamsAPI:
    """Handles interaction with Microsoft Graph API for Teams presence"""
    
    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        """
        Initialize Teams API client
        
        Args:
            tenant_id: Azure AD Tenant ID
            client_id: Azure AD Application ID
            client_secret: Azure AD Client Secret
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        
    def get_access_token(self) -> str:
        """
        Get access token from Microsoft Graph API
        
        Returns:
            OAuth2 access token
        """
        logger.info("Fetching Microsoft Graph access token")
        
        token_url = f'https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token'
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'https://graph.microsoft.com/.default'
        }
        
        try:
            response = requests.post(token_url, data=data, timeout=10)
            
            if response.status_code == 200:
                self.access_token = response.json()['access_token']
                logger.info("Successfully obtained Microsoft Graph access token")
                return self.access_token
            else:
                logger.error(f"Token error: {response.status_code} - {response.text}")
                raise ConnectionError(f"Authentication failed: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Teams token request failed: {e}")
            raise ConnectionError(f"Failed to connect to Microsoft Identity service: {e}")

    def get_user_presence(self, user_id: str, access_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch user presence data
        
        Args:
            user_id: User identification (UPN/email or ID)
            access_token: Optional pre-fetched access token
            
        Returns:
            Dictionary containing availability and activity
        """
        token = access_token or self.access_token
        if not token:
            token = self.get_access_token()
            
        user_id_encoded = urllib.parse.quote(user_id, safe="")
        logger.info(f"Fetching Teams presence for user: {user_id}")
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        url = f'https://graph.microsoft.com/v1.0/users/{user_id_encoded}/presence'
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 401:
                # Token might be expired, clear and retry once
                logger.warning("Access token expired, retrying once")
                self.access_token = None
                return self.get_user_presence(user_id)
                
            if response.status_code == 200:
                data = response.json()
                result = {
                    'availability': data.get('availability', 'Unknown'),
                    'activity': data.get('activity', 'Unknown')
                }
                logger.info(f"Presence for {user_id}: {result['availability']} ({result['activity']})")
                return result
            else:
                logger.error(f"Presence error: {response.status_code} - {response.text}")
                raise ValueError(f"Failed to fetch presence: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Teams presence request failed: {e}")
            raise ConnectionError(f"Failed to connect to Microsoft Graph service: {e}")
