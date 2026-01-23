"""
Playlist Manager for iPIXEL Controller
Handles playlist state, item management, and playback logic
"""

import json
import os
import random
from typing import List, Dict, Any, Optional, Callable
from utils.logger import get_logger

logger = get_logger()


class PlaylistManager:
    """Manages iPIXEL playlists (items, state, and playback flow)"""
    
    def __init__(self, playlists_dir: str, play_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        """
        Initialize playlist manager
        
        Args:
            playlists_dir: Directory where playlist JSON files are stored
            play_callback: Callback function to execute a preset (passed the preset dictionary)
        """
        self.playlists_dir = playlists_dir
        self.playlist: List[Dict[str, Any]] = []
        self.current_index = -1
        self.is_playing = False
        self.is_paused = False
        self.play_callback = play_callback
        
        # Current active timer/handle (to be managed by the engine, e.g. tkinter 'after')
        self.next_preset_timer = None
        
        if not os.path.exists(self.playlists_dir):
            os.makedirs(self.playlists_dir)
            
        logger.info(f"PlaylistManager initialized. Data dir: {self.playlists_dir}")
    
    def set_playlist(self, playlist: List[Dict[str, Any]]):
        """Set the current playlist items"""
        self.playlist = playlist
        self.current_index = -1
        logger.debug(f"Playlist set with {len(playlist)} items")
    
    def add_item(self, preset_name: str, duration: float, use_anim_duration: bool = False):
        """Add an item to the playlist"""
        self.playlist.append({
            'preset_name': preset_name,
            'duration': duration,
            'use_anim_duration': use_anim_duration
        })
        logger.debug(f"Added to playlist: {preset_name} ({duration}s)")
    
    def remove_item(self, index: int) -> bool:
        """Remove an item from the playlist"""
        if 0 <= index < len(self.playlist):
            item = self.playlist.pop(index)
            logger.debug(f"Removed from playlist: {item['preset_name']}")
            return True
        return False
    
    def move_item(self, index: int, direction: int) -> bool:
        """Move an item up (-1) or down (+1)"""
        new_index = index + direction
        if 0 <= index < len(self.playlist) and 0 <= new_index < len(self.playlist):
            self.playlist[index], self.playlist[new_index] = self.playlist[new_index], self.playlist[index]
            return True
        return False
    
    def clear(self):
        """Clear the current playlist"""
        self.playlist = []
        self.current_index = -1
        self.is_playing = False
        logger.debug("Playlist cleared")

    def save_playlist(self, name: str) -> bool:
        """Save current playlist to a file"""
        if not name:
            return False
            
        filename = f"{name}.json" if not name.endswith('.json') else name
        filepath = os.path.join(self.playlists_dir, filename)
        
        try:
            # Wrap in compatibility object
            data = {
                "name": name,
                "items": self.playlist
            }
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Playlist saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save playlist {name}: {e}")
            return False
            
    def load_playlist(self, name: str) -> bool:
        """Load a playlist from a file"""
        filename = f"{name}.json" if not name.endswith('.json') else name
        filepath = os.path.join(self.playlists_dir, filename)
        
        if not os.path.exists(filepath):
            logger.warning(f"Playlist file not found: {filepath}")
            return False
            
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            # Handle both raw list and wrapped object
            if isinstance(data, dict) and 'items' in data:
                self.playlist = data['items']
            elif isinstance(data, list):
                self.playlist = data
            else:
                logger.error(f"Invalid playlist format in {name}")
                return False
                
            self.current_index = -1
            logger.info(f"Loaded playlist {name} with {len(self.playlist)} items")
            return True
        except Exception as e:
            logger.error(f"Failed to load playlist {name}: {e}")
            return False

    def list_playlists(self) -> List[str]:
        """List all available playlist files"""
        try:
            files = [f for f in os.listdir(self.playlists_dir) if f.endswith('.json')]
            return [f[:-5] for f in files]  # Remove .json extension
        except Exception as e:
            logger.error(f"Failed to list playlists: {e}")
            return []
            
    def get_next_item(self) -> Optional[Dict[str, Any]]:
        """Get the next item to play"""
        if not self.playlist:
            return None
            
        self.current_index += 1
        if self.current_index >= len(self.playlist):
            self.current_index = 0  # Loop back to beginning
            
        return self.playlist[self.current_index]

    def start(self):
        """Start playing the playlist"""
        if not self.playlist:
            logger.warning("Attempted to start empty playlist")
            return False
            
        self.is_playing = True
        self.is_paused = False
        logger.info("Playlist started")
        return True
        
    def pause(self):
        """Pause playback"""
        if self.is_playing:
            self.is_paused = True
            logger.info("Playlist paused")
            return True
        return False
        
    def resume(self):
        """Resume playback"""
        if self.is_playing and self.is_paused:
            self.is_paused = False
            logger.info("Playlist resumed")
            return True
        return False
        
    def stop(self):
        """Stop playback"""
        self.is_playing = False
        self.is_paused = False
        self.current_index = -1
        logger.info("Playlist stopped")
        return True
