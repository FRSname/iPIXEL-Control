"""
YouTube API Client for iPIXEL Controller
"""

from typing import Dict, Any, Optional
from utils.logger import get_logger

logger = get_logger()


class YouTubeAPI:
    """Handles interaction with YouTube Data API v3"""
    
    def __init__(self, api_key: str):
        """
        Initialize YouTube API client
        
        Args:
            api_key: YouTube Data API v3 key
        """
        self.api_key = api_key
        self._youtube = None
        
    def _get_client(self):
        """Lazy initialization of the Google API client"""
        if self._youtube is None:
            try:
                from googleapiclient.discovery import build
                self._youtube = build('youtube', 'v3', developerKey=self.api_key)
            except ImportError:
                logger.error("google-api-python-client not installed")
                raise ImportError("Google API library not installed. Please run: pip install google-api-python-client")
        return self._youtube

    def get_channel_stats(self, channel_input: str) -> Dict[str, Any]:
        """
        Fetch YouTube channel statistics
        
        Args:
            channel_input: Channel ID or handle (starting with @)
            
        Returns:
            Dictionary containing channel_title, subscribers, views, and videos
        """
        youtube = self._get_client()
        
        logger.info(f"Fetching YouTube stats for: {channel_input}")
        
        # Handle both @handle and channel ID formats
        if channel_input.startswith('@'):
            # Search for channel by handle
            search_response = youtube.search().list(
                q=channel_input,
                type='channel',
                part='id',
                maxResults=1
            ).execute()
            
            if not search_response.get('items'):
                logger.warning(f"YouTube channel handle not found: {channel_input}")
                raise ValueError(f"Channel not found: {channel_input}")
            
            channel_id = search_response['items'][0]['id']['channelId']
        else:
            channel_id = channel_input
            
        # Get channel statistics
        channel_response = youtube.channels().list(
            part='statistics,snippet',
            id=channel_id
        ).execute()
        
        if not channel_response.get('items'):
            logger.warning(f"YouTube channel ID not found: {channel_id}")
            raise ValueError(f"Channel not found: {channel_input}")
            
        channel_data = channel_response['items'][0]
        stats = channel_data['statistics']
        snippet = channel_data['snippet']
        
        result = {
            'channel_title': snippet['title'],
            'subscribers': int(stats.get('subscriberCount', 0)),
            'views': int(stats.get('viewCount', 0)),
            'videos': int(stats.get('videoCount', 0)),
            'latest_video_views': 0  # Placeholder as per current implementation
        }
        
        logger.info(f"Successfully fetched stats for {result['channel_title']}")
        return result
