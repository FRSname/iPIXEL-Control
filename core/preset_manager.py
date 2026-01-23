"""
Preset Manager for iPIXEL Controller
Handles preset storage, loading, saving, and formatting
"""

import json
import os
import base64
from io import BytesIO
from typing import List, Dict, Any, Optional, Callable
from PIL import Image
from utils.logger import get_logger

logger = get_logger()


class PresetManager:
    """Manages iPIXEL presets (CRUD operations and formatting)"""
    
    def __init__(self, presets_file: str, asset_resolver: Optional[Callable[[str], str]] = None):
        """
        Initialize preset manager
        
        Args:
            presets_file: Path to the JSON presets file
            asset_resolver: Function to resolve relative asset paths to absolute paths
        """
        self.presets_file = presets_file
        self.presets: List[Dict[str, Any]] = []
        self.asset_resolver = asset_resolver
        self.load_presets()
        logger.info(f"PresetManager initialized with {len(self.presets)} presets")
    
    def load_presets(self) -> List[Dict[str, Any]]:
        """Load presets from JSON file"""
        try:
            if os.path.exists(self.presets_file):
                with open(self.presets_file, 'r') as f:
                    self.presets = json.load(f)
            else:
                self.presets = []
        except Exception as e:
            logger.error(f"Failed to load presets: {e}")
            self.presets = []
        return self.presets
    
    def save_presets(self) -> bool:
        """Save presets to JSON file"""
        try:
            with open(self.presets_file, 'w') as f:
                json.dump(self.presets, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save presets: {e}")
            return False
    
    def add_preset(self, preset: Dict[str, Any]) -> int:
        """Add a new preset"""
        self.presets.append(preset)
        self.save_presets()
        return len(self.presets) - 1
    
    def delete_preset(self, index: int) -> bool:
        """Delete a preset by index"""
        if 0 <= index < len(self.presets):
            self.presets.pop(index)
            self.save_presets()
            return True
        return False
    
    def update_preset(self, index: int, preset: Dict[str, Any]) -> bool:
        """Update an existing preset"""
        if 0 <= index < len(self.presets):
            self.presets[index] = preset
            self.save_presets()
            return True
        return False

    def generate_thumbnail(self, image_path: str, max_size=(64, 16)) -> Optional[str]:
        """Generate a thumbnail from an image file and return as base64 string"""
        try:
            # Resolve path if resolver is available
            full_path = self.asset_resolver(image_path) if self.asset_resolver else image_path
            
            if not os.path.exists(full_path):
                logger.warning(f"Thumbnail generation: file not found: {full_path}")
                return None
            
            # Open and resize image
            img = Image.open(full_path)
            
            # Handle animated GIFs - get first frame
            if hasattr(img, 'is_animated') and img.is_animated:
                img.seek(0)
            
            # Convert RGBA to RGB if needed
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (0, 0, 0))
                background.paste(img, mask=img.split()[3])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Crop to fill the thumbnail area (no black borders)
            img_ratio = img.width / img.height
            thumb_ratio = max_size[0] / max_size[1]
            
            if img_ratio > thumb_ratio:
                # Image is wider - crop width
                new_height = max_size[1]
                new_width = int(new_height * img_ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                left = (new_width - max_size[0]) // 2
                img = img.crop((left, 0, left + max_size[0], max_size[1]))
            else:
                # Image is taller - crop height
                new_width = max_size[0]
                new_height = int(new_width / img_ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                top = (new_height - max_size[1]) // 2
                img = img.crop((0, top, max_size[0], top + max_size[1]))
            
            # Convert to base64
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            return img_str
        except Exception as e:
            logger.error(f"Failed to generate thumbnail: {e}")
            return None
    
    def get_preview_text(self, preset: Dict[str, Any]) -> str:
        """Generate preview text for a preset"""
        preset_type = preset.get('type', 'unknown')
        
        if preset_type == "text":
            text = preset.get('text', '')
            return text[:15] if len(text) <= 15 else text[:12] + "..."
        elif preset_type == "image":
            return "🖼️ Image"
        elif preset_type == "stock":
            ticker = preset.get('ticker', 'STOCK')
            return f"📈 {ticker}"
        elif preset_type == "youtube":
            channel = preset.get('channel', 'Channel')
            if channel.startswith('@'):
                return f"📺 {channel}"
            return "📺 YouTube"
        elif preset_type == "weather":
            location = preset.get('location', 'Location')
            return f"🌤️ {location}"
        elif preset_type == "animation":
            anim_type = preset.get('anim_type', 'animation')
            anim_names = {
                'game_of_life': '🎨 Life',
                'matrix': '🎨 Matrix',
                'fire': '🎨 Fire',
                'starfield': '🎨 Stars',
                'plasma': '🎨 Plasma'
            }
            return anim_names.get(anim_type, '🎨 Anim')
        elif preset_type == "clock":
            clock_mode = preset.get('clock_mode', 'builtin')
            if clock_mode == 'custom':
                import time
                format_preview = preset.get('time_format', '%H:%M:%S')
                return time.strftime(format_preview)
            elif clock_mode == 'countdown':
                event = preset.get('countdown_event', 'Event')
                return f"⏱️ {event}"
            else:
                return "🕐 Clock"
        return "..."
    
    def get_details_text(self, preset: Dict[str, Any]) -> str:
        """Generate detail description for a preset"""
        preset_type = preset.get('type', 'unknown')
        
        if preset_type == "text":
            anim_names = {0: "Static", 1: "Scroll L", 2: "Scroll R", 4: "Flash"}
            anim = anim_names.get(preset.get('animation', 0), "Anim")
            rainbow = preset.get('rainbow', 0)
            if rainbow > 0:
                return f"{anim}, Rainbow {rainbow}"
            return anim
        elif preset_type == "image":
            path = preset.get('image_path', '')
            filename = os.path.basename(path) if path else "No file"
            return filename
        elif preset_type == "stock":
            ticker = preset.get('ticker', 'UNKNOWN')
            format_type = preset.get('format', 'price_change')
            format_names = {
                'price_change': 'Price + Change',
                'price_only': 'Price Only',
                'ticker_price': 'Ticker + Price'
            }
            auto_refresh = " (Auto)" if preset.get('auto_refresh', False) else ""
            return f"{ticker} - {format_names.get(format_type, format_type)}{auto_refresh}"
        elif preset_type == "youtube":
            channel = preset.get('channel', 'Unknown')
            auto_refresh = " (Auto)" if preset.get('auto_refresh', False) else ""
            return f"Logo + Subscribers{auto_refresh}"
        elif preset_type == "weather":
            location = preset.get('location', 'Unknown')
            unit = preset.get('unit', 'metric')
            unit_symbol = "°C" if unit == "metric" else "°F"
            auto_refresh = " (Auto)" if preset.get('auto_refresh', False) else ""
            return f"{location} ({unit_symbol}){auto_refresh}"
        elif preset_type == "animation":
            anim_type = preset.get('anim_type', 'game_of_life')
            anim_names = {
                'game_of_life': "Conway's Life",
                'matrix': 'Matrix Rain',
                'fire': 'Fire Effect',
                'starfield': 'Starfield',
                'plasma': 'Plasma'
            }
            color_scheme = preset.get('color_scheme', 'white')
            fps = preset.get('speed', 10)
            return f"{anim_names.get(anim_type, anim_type)} - {color_scheme.title()} @ {fps}fps"
        elif preset_type == "clock":
            clock_mode = preset.get('clock_mode', 'builtin')
            if clock_mode == 'custom':
                format_map = {
                    "%H:%M:%S": "24h with seconds",
                    "%H:%M": "24h",
                    "%I:%M:%S %p": "12h with seconds",
                    "%I:%M %p": "12h",
                }
                fmt = preset.get('time_format', '%H:%M:%S')
                return format_map.get(fmt, "Custom time")
            elif clock_mode == 'countdown':
                year = preset.get('countdown_year', 2026)
                month = preset.get('countdown_month', 1)
                day = preset.get('countdown_day', 1)
                return f"To {year}-{month:02d}-{day:02d}"
            else:
                style = preset.get('clock_style', 0)
                return f"Built-in style {style}"
        return "Unknown preset type"
