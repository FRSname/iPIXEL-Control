"""
Text control tab for iPIXEL Controller
"""

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from ui.tabs.base_tab import BaseTab

if TYPE_CHECKING:
    from ipixel_controller import iPixelController


class TextTab(BaseTab):
    """Tab for text-based display control"""
    
    def __init__(self, parent: ttk.Notebook, controller: 'iPixelController'):
        super().__init__(parent, controller, "Text")

    def setup_ui(self):
        """Build the text control UI"""
        self.content.columnconfigure(1, weight=1)
        self.content.rowconfigure(1, weight=1)
        
        # Text input
        ttk.Label(self.content, text="Text:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # Access variables from controller
        self.controller.text_input = tk.Text(self.content, height=5, width=40)
        self.controller.text_input.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Text color
        ttk.Label(self.content, text="Text Color:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        
        color_frame = ttk.Frame(self.content)
        color_frame.grid(row=2, column=1, sticky=tk.W, pady=(0, 5))
        
        self.controller.text_color = "#FFFFFF"
        self.controller.text_color_canvas = tk.Canvas(color_frame, width=30, height=20, bg=self.controller.text_color, relief=tk.SUNKEN)
        self.controller.text_color_canvas.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(color_frame, text="Choose", command=self.controller.choose_text_color).pack(side=tk.LEFT)
        
        # Background color
        ttk.Label(self.content, text="Background:").grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        
        bg_frame = ttk.Frame(self.content)
        bg_frame.grid(row=3, column=1, sticky=tk.W, pady=(0, 10))
        
        self.controller.bg_color = "#FFFFFF"
        self.controller.bg_color_canvas = tk.Canvas(bg_frame, width=30, height=20, bg=self.controller.bg_color, relief=tk.SUNKEN)
        self.controller.bg_color_canvas.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(bg_frame, text="Choose", command=self.controller.choose_bg_color).pack(side=tk.LEFT)
        
        # Animation
        ttk.Label(self.content, text="Animation:").grid(row=4, column=0, sticky=tk.W, pady=(0, 5))
        
        self.controller.animation_var = tk.IntVar(value=0)
        animation_frame = ttk.Frame(self.content)
        animation_frame.grid(row=4, column=1, sticky=tk.W, pady=(0, 5))
        
        animations = [
            ("Static", 0),
            ("Scroll Left", 1),
            ("Scroll Right", 2),
            ("Flash", 5),
        ]
        for text, value in animations:
            ttk.Radiobutton(animation_frame, text=text, variable=self.controller.animation_var, value=value).pack(side=tk.LEFT, padx=(0, 5))
        
        # Speed (for animations)
        ttk.Label(self.content, text="Speed:").grid(row=5, column=0, sticky=tk.W, pady=(0, 5))
        
        self.controller.speed_var = tk.IntVar(value=50)
        speed_frame = ttk.Frame(self.content)
        speed_frame.grid(row=5, column=1, sticky=tk.W, pady=(0, 5))
        
        ttk.Scale(speed_frame, from_=10, to=100, variable=self.controller.speed_var, orient=tk.HORIZONTAL, length=200).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(speed_frame, textvariable=self.controller.speed_var).pack(side=tk.LEFT)
        
        # Rainbow mode (animated color effects)
        ttk.Label(self.content, text="Rainbow Effect:").grid(row=6, column=0, sticky=tk.W, pady=(0, 5))
        
        self.controller.rainbow_var = tk.IntVar(value=0)
        rainbow_frame = ttk.Frame(self.content)
        rainbow_frame.grid(row=6, column=1, sticky=tk.W, pady=(0, 5))
        
        rainbow_row1 = ttk.Frame(rainbow_frame)
        rainbow_row1.pack(anchor=tk.W)
        rainbow_row2 = ttk.Frame(rainbow_frame)
        rainbow_row2.pack(anchor=tk.W)
        
        rainbow_modes = [
            ("None", 0),
            ("Mode 1", 1),
            ("Mode 2", 2),
            ("Mode 3", 3),
            ("Mode 4", 4),
            ("Mode 5", 5),
            ("Mode 6", 6),
            ("Mode 7", 7),
            ("Mode 8", 8),
            ("Mode 9", 9),
        ]
        for i, (text, value) in enumerate(rainbow_modes):
            parent = rainbow_row1 if i < 5 else rainbow_row2
            ttk.Radiobutton(parent, text=text, variable=self.controller.rainbow_var, value=value).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(self.content, text="(Different rainbow modes create various color effects)", 
                 font=('TkDefaultFont', 8, 'italic')).grid(row=8, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))

        # Sprite font (custom text)
        sprite_frame = ttk.LabelFrame(self.content, text="Sprite Font", padding="8")
        sprite_frame.grid(row=9, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        sprite_frame.columnconfigure(1, weight=1)

        self.controller.text_use_sprite_var = tk.BooleanVar(value=self.controller.settings.get('text_use_sprite_font', False))
        ttk.Checkbutton(
            sprite_frame,
            text="Use sprite font",
            variable=self.controller.text_use_sprite_var,
            command=self.controller.update_text_sprite_settings
        ).grid(row=0, column=0, sticky=tk.W)

        ttk.Label(sprite_frame, text="Font:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.controller.text_sprite_font_var = tk.StringVar(value=self.controller.settings.get('text_sprite_font_name', ''))
        self.controller.text_sprite_font_combo = ttk.Combobox(sprite_frame, textvariable=self.controller.text_sprite_font_var, state="readonly")
        self.controller.text_sprite_font_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(5, 0))
        self.controller.text_sprite_font_combo.bind('<<ComboboxSelected>>', lambda e: self.controller.update_text_sprite_settings())

        ttk.Label(sprite_frame, text="Note: Sprite font ignores animation/rainbow.", foreground="gray").grid(
            row=2, column=0, columnspan=2, sticky=tk.W, pady=(2, 0)
        )

        ttk.Label(self.content, text="Static delay (s):").grid(row=10, column=0, sticky=tk.W, pady=(0, 5))
        self.controller.text_static_delay_var = tk.IntVar(value=self.controller.settings.get('text_static_delay_seconds', 2))
        ttk.Spinbox(self.content, from_=1, to=30, textvariable=self.controller.text_static_delay_var, width=5,
                    command=self.controller.update_text_sprite_settings).grid(row=10, column=1, sticky=tk.W, pady=(0, 5))
        
        # Send button
        self.controller.send_text_btn = ttk.Button(self.content, text="Send Text", command=self.controller.send_text, state=tk.DISABLED)
        self.controller.send_text_btn.grid(row=11, column=0, columnspan=2, pady=(10, 0))
