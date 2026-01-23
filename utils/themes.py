"""
Theme configuration for iPIXEL Controller
Provides light and dark mode with easy switching
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class ThemeColors:
    """Color scheme for a theme"""
    bg: str  # Background
    fg: str  # Foreground (text)
    button_bg: str
    button_fg: str
    button_active: str
    entry_bg: str
    entry_fg: str
    frame_bg: str
    highlight: str
    accent: str
    error: str
    success: str
    

# Light Theme (default)
LIGHT_THEME = ThemeColors(
    bg='#f0f0f0',
    fg='#000000',
    button_bg='#e0e0e0',
    button_fg='#000000',
    button_active='#d0d0d0',
    entry_bg='#ffffff',
    entry_fg='#000000',
    frame_bg='#f5f5f5',
    highlight='#0078d4',
    accent='#0066cc',
    error='#d32f2f',
    success='#388e3c'
)

# Dark Theme
DARK_THEME = ThemeColors(
    bg='#1e1e1e',
    fg='#e0e0e0',
    button_bg='#2d2d30',
    button_fg='#e0e0e0',
    button_active='#3e3e42',
    entry_bg='#2b2b2b',
    entry_fg='#ffffff',
    frame_bg='#252526',
    highlight='#0e639c',
    accent='#007acc',
    error='#f44336',
    success='#4caf50'
)


class ThemeManager:
    """Manages application themes"""
    
    _instance = None
    _current_theme = 'light'
    _themes = {
        'light': LIGHT_THEME,
        'dark': DARK_THEME
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ThemeManager, cls).__new__(cls)
        return cls._instance
    
    def get_current_theme(self) -> str:
        """Get current theme name"""
        return self._current_theme
    
    def get_colors(self) -> ThemeColors:
        """Get current theme colors"""
        return self._themes[self._current_theme]
    
    def set_theme(self, theme_name: str):
        """Set the current theme"""
        if theme_name in self._themes:
            self._current_theme = theme_name
        else:
            raise ValueError(f"Unknown theme: {theme_name}")
    
    def toggle_theme(self):
        """Toggle between light and dark mode"""
        self._current_theme = 'dark' if self._current_theme == 'light' else 'light'
        return self._current_theme
    
    def get_available_themes(self) -> list:
        """Get list of available theme names"""
        return list(self._themes.keys())


# Convenience functions
def get_theme_manager() -> ThemeManager:
    """Get the theme manager instance"""
    return ThemeManager()


def get_colors() -> ThemeColors:
    """Get current theme colors"""
    return ThemeManager().get_colors()


def set_theme(theme_name: str):
    """Set theme by name"""
    ThemeManager().set_theme(theme_name)


def toggle_theme() -> str:
    """Toggle theme and return new theme name"""
    return ThemeManager().toggle_theme()
