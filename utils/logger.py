"""
Logging utility for iPIXEL Controller
Provides centralized logging with file rotation and configurable levels
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


class iPIXELLogger:
    """Centralized logger for the application"""
    
    _instance = None
    _logger = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(iPIXELLogger, cls).__new__(cls)
            cls._instance._initialize_logger()
        return cls._instance
    
    def _initialize_logger(self):
        """Initialize the logger with file and console handlers"""
        self._logger = logging.getLogger('iPIXEL')
        self._logger.setLevel(logging.DEBUG)
        
        # Create logs directory if it doesn't exist
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # File handler with rotation (max 5MB, keep 5 backup files)
        log_file = log_dir / 'ipixel_controller.log'
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        self._logger.addHandler(file_handler)
        self._logger.addHandler(console_handler)
    
    def get_logger(self):
        """Get the logger instance"""
        return self._logger
    
    def set_debug_mode(self, debug: bool):
        """Enable or disable debug mode"""
        if debug:
            self._logger.setLevel(logging.DEBUG)
            for handler in self._logger.handlers:
                if isinstance(handler, logging.StreamHandler):
                    handler.setLevel(logging.DEBUG)
        else:
            self._logger.setLevel(logging.INFO)
            for handler in self._logger.handlers:
                if isinstance(handler, logging.StreamHandler):
                    handler.setLevel(logging.INFO)


# Convenience functions for easy import
def get_logger():
    """Get the application logger"""
    return iPIXELLogger().get_logger()


def set_debug_mode(debug: bool):
    """Set debug mode"""
    iPIXELLogger().set_debug_mode(debug)


# Example usage in other modules:
# from utils.logger import get_logger
# logger = get_logger()
# logger.info("Connection established")
# logger.error("Failed to connect", exc_info=True)
