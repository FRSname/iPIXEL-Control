"""
Base module for iPIXEL Controller UI tabs
"""

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ipixel_controller import iPixelController


class BaseTab:
    """Base class for all application tabs"""
    
    def __init__(self, parent: ttk.Notebook, controller: 'iPixelController', tab_name: str):
        """
        Initialize the tab
        
        Args:
            parent: The notebook widget containing the tabs
            controller: The main application controller instance
            tab_name: The display name for the tab
        """
        self.parent = parent
        self.controller = controller
        self.tab_name = tab_name
        self.frame = ttk.Frame(parent)
        parent.add(self.frame, text=tab_name)
        
        # Add padding to the main frame
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)
        
        # Content frame with padding
        self.content = ttk.Frame(self.frame, padding="10")
        self.content.grid(row=0, column=0, sticky="nsew")
        
        self.setup_ui()

    def setup_ui(self):
        """Override this method to build the tab's UI"""
        raise NotImplementedError("Subclasses must implement setup_ui")

    def update_status(self, message: str):
        """Helper to update application status via controller"""
        if hasattr(self.controller, 'status_var'):
            self.controller.status_var.set(message)
