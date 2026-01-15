#!/usr/bin/env python3
"""
iPixel LED Panel Controller e
A desktop application to control iPixel Color LED matrix displays via Bluetooth
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser
import asyncio
import threading
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os
import sys
import tempfile
import json

try:
    from pypixelcolor import Client
    from bleak import BleakScanner
except ImportError:
    print("Required libraries not installed. Please run: pip install pypixelcolor bleak pillow")
    sys.exit(1)


class iPixelController:
    def __init__(self, root):
        self.root = root
        self.root.title("iPixel LED Panel Controller")
        self.root.geometry("800x600")
        
        self.client = None
        self.device_address = None
        self.is_connected = False
        self.loop = None
        
        # Initialize presets
        self.presets_file = "ipixel_presets.json"
        self.settings_file = "ipixel_settings.json"
        self.presets = []
        self.thumbnail_cache = {}  # Cache for PhotoImage objects
        self.load_presets()
        self.settings = self.load_settings()
        
        # Setup UI
        self.setup_ui()
        
        # Start async event loop in separate thread
        self.start_event_loop()
        
        # Auto-connect to last device if enabled
        if self.settings.get('auto_connect', True):
            self.root.after(1000, self.auto_connect_to_last_device)
            # Restore last state after connection
            if self.settings.get('restore_last_state', True):
                self.root.after(3000, self.restore_last_state)
        
    def setup_ui(self):
        """Create the user interface"""
        
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Connection Section
        connection_frame = ttk.LabelFrame(main_frame, text="Connection", padding="10")
        connection_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        connection_frame.columnconfigure(1, weight=1)
        
        ttk.Label(connection_frame, text="Device:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(connection_frame, textvariable=self.device_var, state="readonly")
        self.device_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        self.scan_btn = ttk.Button(connection_frame, text="Scan", command=self.scan_devices)
        self.scan_btn.grid(row=0, column=2, padx=(0, 5))
        
        self.connect_btn = ttk.Button(connection_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=3)
        
        self.status_label = ttk.Label(connection_frame, text="Not connected", foreground="red")
        self.status_label.grid(row=1, column=0, columnspan=4, pady=(5, 0))
        
        # Notebook for different control modes
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        main_frame.rowconfigure(1, weight=1)
        
        # Control Board Tab (first for quick access)
        self.create_control_board_tab()
        
        # Text Tab
        self.create_text_tab()
        
        # Image Tab
        self.create_image_tab()
        
        # Text+Image Overlay Tab
        self.create_overlay_tab()
        
        # Clock Tab
        self.create_clock_tab()
        
        # Settings Tab
        self.create_settings_tab()
        
    def create_control_board_tab(self):
        """Create the control board with preset buttons"""
        control_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(control_frame, text="Control Board")
        
        control_frame.columnconfigure(0, weight=1)
        
        # Info
        info_label = ttk.Label(control_frame, 
                              text="Quick access to saved presets. Create presets in other tabs and save them here.",
                              font=('TkDefaultFont', 9, 'italic'), wraplength=750)
        info_label.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Preset buttons area
        self.presets_frame = ttk.LabelFrame(control_frame, text="Saved Presets", padding="10")
        self.presets_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        control_frame.rowconfigure(1, weight=1)
        
        # Container for preset buttons (with scrollbar)
        canvas_frame = ttk.Frame(self.presets_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.presets_canvas = tk.Canvas(canvas_frame, height=400)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.presets_canvas.yview)
        self.presets_scrollable_frame = ttk.Frame(self.presets_canvas)
        
        self.presets_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.presets_canvas.configure(scrollregion=self.presets_canvas.bbox("all"))
        )
        
        self.presets_canvas.create_window((0, 0), window=self.presets_scrollable_frame, anchor="nw")
        self.presets_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.presets_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Playlist section
        playlist_frame = ttk.LabelFrame(control_frame, text="🎵 Playlist - Auto Switch Presets", padding="10")
        playlist_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 10))
        
        # Playlist controls
        playlist_control_frame = ttk.Frame(playlist_frame)
        playlist_control_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(playlist_control_frame, text="▶️ Play", 
                  command=self.play_playlist, width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(playlist_control_frame, text="⏸️ Pause", 
                  command=self.pause_playlist, width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(playlist_control_frame, text="⏹️ Stop", 
                  command=self.stop_playlist, width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(playlist_control_frame, text="✏️ Edit Playlist", 
                  command=self.edit_playlist, width=15).pack(side=tk.LEFT, padx=(10, 0))
        
        # Playlist management buttons (second row)
        playlist_manage_frame = ttk.Frame(playlist_frame)
        playlist_manage_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(playlist_manage_frame, text="💾 Save Playlist As...", 
                  command=self.save_playlist, width=18).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(playlist_manage_frame, text="📂 Load Playlist", 
                  command=self.load_playlist_dialog, width=18).pack(side=tk.LEFT, padx=(0, 5))
        
        # Current playlist name
        self.current_playlist_name_var = tk.StringVar(value="(Unsaved playlist)")
        ttk.Label(playlist_manage_frame, textvariable=self.current_playlist_name_var, 
                 font=('TkDefaultFont', 8, 'italic'), foreground='gray').pack(side=tk.LEFT, padx=(10, 0))
        
        # Playlist status
        self.playlist_status_var = tk.StringVar(value="Playlist: Not running")
        ttk.Label(playlist_control_frame, textvariable=self.playlist_status_var, 
                 font=('TkDefaultFont', 9, 'italic')).pack(side=tk.LEFT, padx=(20, 0))
        
        # Action buttons
        action_frame = ttk.Frame(control_frame)
        action_frame.grid(row=3, column=0, pady=(10, 0))
        
        ttk.Button(action_frame, text="➕ Save Current as Preset", 
                  command=self.save_current_preset).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_frame, text="📁 Import Presets", 
                  command=self.import_presets).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_frame, text="💾 Export Presets", 
                  command=self.export_presets).pack(side=tk.LEFT)
        
        # Initialize playlist state
        self.playlist = []
        self.current_playlist_file = None  # Track current playlist file
        self.playlist_running = False
        self.playlist_paused = False
        self.playlist_index = 0
        self.playlist_timer = None
        
        # Render preset buttons
        self.refresh_preset_buttons()
        
    def create_text_tab(self):
        """Create the text control tab"""
        text_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(text_frame, text="Text")
        
        text_frame.columnconfigure(1, weight=1)
        text_frame.rowconfigure(1, weight=1)
        
        # Text input
        ttk.Label(text_frame, text="Text:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        self.text_input = tk.Text(text_frame, height=5, width=40)
        self.text_input.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Text color
        ttk.Label(text_frame, text="Text Color:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        
        color_frame = ttk.Frame(text_frame)
        color_frame.grid(row=2, column=1, sticky=tk.W, pady=(0, 5))
        
        self.text_color = "#FFFFFF"
        self.text_color_canvas = tk.Canvas(color_frame, width=30, height=20, bg=self.text_color, relief=tk.SUNKEN)
        self.text_color_canvas.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(color_frame, text="Choose", command=self.choose_text_color).pack(side=tk.LEFT)
        
        # Background color
        ttk.Label(text_frame, text="Background:").grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        
        bg_frame = ttk.Frame(text_frame)
        bg_frame.grid(row=3, column=1, sticky=tk.W, pady=(0, 10))
        
        self.bg_color = "#000000"
        self.bg_color_canvas = tk.Canvas(bg_frame, width=30, height=20, bg=self.bg_color, relief=tk.SUNKEN)
        self.bg_color_canvas.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(bg_frame, text="Choose", command=self.choose_bg_color).pack(side=tk.LEFT)
        
        # Font size (char_height)
        ttk.Label(text_frame, text="Character Height:").grid(row=4, column=0, sticky=tk.W, pady=(0, 5))
        
        self.font_size_var = tk.IntVar(value=16)
        font_size_frame = ttk.Frame(text_frame)
        font_size_frame.grid(row=4, column=1, sticky=tk.W, pady=(0, 5))
        
        ttk.Radiobutton(font_size_frame, text="16px", variable=self.font_size_var, value=16).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(font_size_frame, text="32px", variable=self.font_size_var, value=32).pack(side=tk.LEFT)
        
        # Animation
        ttk.Label(text_frame, text="Animation:").grid(row=5, column=0, sticky=tk.W, pady=(0, 5))
        
        self.animation_var = tk.IntVar(value=0)
        animation_frame = ttk.Frame(text_frame)
        animation_frame.grid(row=5, column=1, sticky=tk.W, pady=(0, 5))
        
        animations = [
            ("Static", 0),
            ("Scroll Left", 1),
            ("Scroll Right", 2),
            ("Flash", 5),
        ]
        for text, value in animations:
            ttk.Radiobutton(animation_frame, text=text, variable=self.animation_var, value=value).pack(side=tk.LEFT, padx=(0, 5))
        
        # Speed (for animations)
        ttk.Label(text_frame, text="Speed:").grid(row=6, column=0, sticky=tk.W, pady=(0, 5))
        
        self.speed_var = tk.IntVar(value=50)
        speed_frame = ttk.Frame(text_frame)
        speed_frame.grid(row=6, column=1, sticky=tk.W, pady=(0, 5))
        
        ttk.Scale(speed_frame, from_=10, to=100, variable=self.speed_var, orient=tk.HORIZONTAL, length=200).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(speed_frame, textvariable=self.speed_var).pack(side=tk.LEFT)
        
        # Rainbow mode (animated color effects)
        ttk.Label(text_frame, text="Rainbow Effect:").grid(row=7, column=0, sticky=tk.W, pady=(0, 5))
        
        self.rainbow_var = tk.IntVar(value=0)
        rainbow_frame = ttk.Frame(text_frame)
        rainbow_frame.grid(row=7, column=1, sticky=tk.W, pady=(0, 5))
        
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
            ttk.Radiobutton(parent, text=text, variable=self.rainbow_var, value=value).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(text_frame, text="(Different rainbow modes create various color effects)", 
                 font=('TkDefaultFont', 8, 'italic')).grid(row=8, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # Send button
        self.send_text_btn = ttk.Button(text_frame, text="Send Text", command=self.send_text, state=tk.DISABLED)
        self.send_text_btn.grid(row=9, column=0, columnspan=2, pady=(10, 0))
        
    def create_image_tab(self):
        """Create the image control tab"""
        image_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(image_frame, text="Image")
        
        image_frame.columnconfigure(0, weight=1)
        image_frame.rowconfigure(1, weight=1)
        
        # Resolution info
        info_frame = ttk.LabelFrame(image_frame, text="Display Resolution & Animation Support", padding="10")
        info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        info_text = "Your Display: 16x64 pixels (rectangular)\n\n" \
                   "Supported Formats:\n" \
                   "• Static Images: PNG, JPG, BMP (64x16 pixels recommended)\n" \
                   "• Animated: GIF files (will play animation loop)\n\n" \
                   "Create images at 64x16 pixels for best results.\n" \
                   "GIF animations will loop continuously on the display."
        ttk.Label(info_frame, text=info_text, justify=tk.LEFT).pack()
        
        # Image preview
        self.image_preview_frame = ttk.LabelFrame(image_frame, text="Preview", padding="10")
        self.image_preview_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.image_preview_label = ttk.Label(self.image_preview_frame, text="No image loaded")
        self.image_preview_label.pack()
        
        self.image_path = None
        
        # Buttons
        btn_frame = ttk.Frame(image_frame)
        btn_frame.grid(row=2, column=0, pady=(0, 10))
        
        ttk.Button(btn_frame, text="Load Image", command=self.load_image).pack(side=tk.LEFT, padx=(0, 5))
        self.send_image_btn = ttk.Button(btn_frame, text="Send Image", command=self.send_image, state=tk.DISABLED)
        self.send_image_btn.pack(side=tk.LEFT)
        
    def create_overlay_tab(self):
        """Create the text+image overlay tab"""
        overlay_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(overlay_frame, text="Text+Image")
        
        overlay_frame.columnconfigure(1, weight=1)
        
        # Info
        info_label = ttk.Label(overlay_frame, text="Display text overlay on top of a background image", 
                              font=('TkDefaultFont', 9, 'italic'))
        info_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # Background image
        ttk.Label(overlay_frame, text="Background Image:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        
        bg_img_frame = ttk.Frame(overlay_frame)
        bg_img_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.overlay_bg_path = None
        self.overlay_bg_label = ttk.Label(bg_img_frame, text="No image selected")
        self.overlay_bg_label.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(bg_img_frame, text="Load Background", command=self.load_overlay_bg).pack(side=tk.LEFT)
        
        # Text input
        ttk.Label(overlay_frame, text="Overlay Text:").grid(row=2, column=0, sticky=tk.W, pady=(10, 5))
        
        self.overlay_text_input = tk.Text(overlay_frame, height=3, width=40)
        self.overlay_text_input.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Text color
        ttk.Label(overlay_frame, text="Text Color:").grid(row=4, column=0, sticky=tk.W, pady=(0, 5))
        
        overlay_color_frame = ttk.Frame(overlay_frame)
        overlay_color_frame.grid(row=4, column=1, sticky=tk.W, pady=(0, 5))
        
        self.overlay_text_color = "#FFFFFF"
        self.overlay_text_color_canvas = tk.Canvas(overlay_color_frame, width=30, height=20, 
                                                    bg=self.overlay_text_color, relief=tk.SUNKEN)
        self.overlay_text_color_canvas.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(overlay_color_frame, text="Choose", command=self.choose_overlay_text_color).pack(side=tk.LEFT)
        
        # Font size
        ttk.Label(overlay_frame, text="Font Size:").grid(row=5, column=0, sticky=tk.W, pady=(0, 5))
        
        self.overlay_font_size_var = tk.IntVar(value=12)
        overlay_font_frame = ttk.Frame(overlay_frame)
        overlay_font_frame.grid(row=5, column=1, sticky=tk.W, pady=(0, 5))
        
        ttk.Scale(overlay_font_frame, from_=8, to=24, variable=self.overlay_font_size_var, 
                 orient=tk.HORIZONTAL, length=200).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(overlay_font_frame, textvariable=self.overlay_font_size_var).pack(side=tk.LEFT)
        
        # Font style (bold option)
        ttk.Label(overlay_frame, text="Font Style:").grid(row=6, column=0, sticky=tk.W, pady=(0, 5))
        
        self.overlay_bold_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(overlay_frame, text="Bold", variable=self.overlay_bold_var).grid(row=6, column=1, sticky=tk.W, pady=(0, 5))
        
        # Text position
        ttk.Label(overlay_frame, text="Text Position:").grid(row=7, column=0, sticky=tk.W, pady=(0, 5))
        
        self.overlay_position_var = tk.StringVar(value="center")
        position_frame = ttk.Frame(overlay_frame)
        position_frame.grid(row=7, column=1, sticky=tk.W, pady=(0, 10))
        
        positions = [("Top", "top"), ("Center", "center"), ("Bottom", "bottom")]
        for text, value in positions:
            ttk.Radiobutton(position_frame, text=text, variable=self.overlay_position_var, 
                          value=value).pack(side=tk.LEFT, padx=(0, 5))
        
        # Preview and Send
        preview_frame = ttk.Frame(overlay_frame)
        preview_frame.grid(row=8, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(preview_frame, text="Preview", command=self.preview_overlay).pack(side=tk.LEFT, padx=(0, 5))
        self.send_overlay_btn = ttk.Button(preview_frame, text="Send to Display", 
                                          command=self.send_overlay, state=tk.DISABLED)
        self.send_overlay_btn.pack(side=tk.LEFT)
        
        # Preview area
        self.overlay_preview_frame = ttk.LabelFrame(overlay_frame, text="Preview", padding="10")
        self.overlay_preview_frame.grid(row=9, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        
        self.overlay_preview_label = ttk.Label(self.overlay_preview_frame, text="No preview")
        self.overlay_preview_label.pack()
        
        self.overlay_preview_image = None  # Store the PIL image
        
    def create_clock_tab(self):
        """Create the clock control tab"""
        clock_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(clock_frame, text="Clock")
        
        ttk.Label(clock_frame, text="Display current time on the LED panel", 
                 font=('TkDefaultFont', 10, 'bold')).pack(pady=(0, 10))
        
        # Clock mode selection
        self.clock_mode_var = tk.StringVar(value="builtin")
        
        mode_frame = ttk.LabelFrame(clock_frame, text="Clock Mode", padding="10")
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Radiobutton(mode_frame, text="Built-in Hardware Clock (static styles)", 
                       variable=self.clock_mode_var, value="builtin",
                       command=self.update_clock_options).pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="Custom Design (live updating)", 
                       variable=self.clock_mode_var, value="custom",
                       command=self.update_clock_options).pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="Countdown Timer (count to event)", 
                       variable=self.clock_mode_var, value="countdown",
                       command=self.update_clock_options).pack(anchor=tk.W)
        
        # Built-in clock styles
        self.builtin_frame = ttk.LabelFrame(clock_frame, text="Built-in Clock Styles", padding="10")
        self.builtin_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(self.builtin_frame, text="Select style:", 
                 font=('TkDefaultFont', 9, 'italic')).pack(anchor=tk.W, pady=(0, 5))
        
        self.clock_style_var = tk.IntVar(value=0)
        styles = ["Style 0", "Style 1", "Style 2", "Style 3", "Style 4", 
                 "Style 5", "Style 6", "Style 7", "Style 8"]
        
        style_grid = ttk.Frame(self.builtin_frame)
        style_grid.pack(fill=tk.X)
        
        for i, style in enumerate(styles):
            row = i // 3
            col = i % 3
            ttk.Radiobutton(style_grid, text=style, variable=self.clock_style_var, 
                          value=i).grid(row=row, column=col, sticky=tk.W, padx=10, pady=2)
        
        # Custom clock designs
        self.custom_frame = ttk.LabelFrame(clock_frame, text="Custom Clock Design", padding="10")
        self.custom_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(self.custom_frame, text="Time Format:", 
                 font=('TkDefaultFont', 9, 'italic')).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        self.time_format_var = tk.StringVar(value="%H:%M:%S")
        
        formats = [
            ("24h with seconds (HH:MM:SS)", "%H:%M:%S"),
            ("24h without seconds (HH:MM)", "%H:%M"),
            ("12h with seconds (HH:MM:SS AM/PM)", "%I:%M:%S %p"),
            ("12h without seconds (HH:MM AM/PM)", "%I:%M %p"),
            ("Time & Date (HH:MM DD/MM)", "%H:%M %d/%m"),
            ("Minimal (HH:MM)", "%H:%M"),
            ("With day (Mon HH:MM)", "%a %H:%M"),
        ]
        
        for i, (label, fmt) in enumerate(formats):
            ttk.Radiobutton(self.custom_frame, text=label, variable=self.time_format_var, 
                          value=fmt).grid(row=i+1, column=0, sticky=tk.W, pady=2)
        
        # Custom clock color settings
        color_frame = ttk.Frame(self.custom_frame)
        color_frame.grid(row=len(formats)+1, column=0, sticky=tk.W, pady=(10, 5))
        
        ttk.Label(color_frame, text="Text Color:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.clock_color = "#00ffff"  # Cyan default (lowercase)
        self.clock_color_canvas = tk.Canvas(color_frame, width=30, height=20, 
                                            bg=self.clock_color, relief=tk.SUNKEN)
        self.clock_color_canvas.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(color_frame, text="Choose", command=self.choose_clock_color).pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Label(color_frame, text="Background:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.clock_bg_color = "#000000"
        self.clock_bg_color_canvas = tk.Canvas(color_frame, width=30, height=20, 
                                               bg=self.clock_bg_color, relief=tk.SUNKEN)
        self.clock_bg_color_canvas.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(color_frame, text="Choose", command=self.choose_clock_bg_color).pack(side=tk.LEFT)
        
        # Custom clock animation
        anim_frame = ttk.Frame(self.custom_frame)
        anim_frame.grid(row=len(formats)+2, column=0, sticky=tk.W, pady=(5, 0))
        
        ttk.Label(anim_frame, text="Animation:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.clock_animation_var = tk.StringVar(value="static")
        clock_animations = ["Static", "Scroll Left", "Flash"]
        
        for anim in clock_animations:
            ttk.Radiobutton(anim_frame, text=anim, variable=self.clock_animation_var, 
                          value=anim.lower().replace(" ", "_")).pack(side=tk.LEFT, padx=5)
        
        # Update interval for custom clocks
        interval_frame = ttk.Frame(self.custom_frame)
        interval_frame.grid(row=len(formats)+3, column=0, sticky=tk.W, pady=(5, 0))
        
        ttk.Label(interval_frame, text="Update every:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.clock_update_interval_var = tk.IntVar(value=1)
        ttk.Spinbox(interval_frame, from_=1, to=60, textvariable=self.clock_update_interval_var, 
                   width=5).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(interval_frame, text="second(s)").pack(side=tk.LEFT)
        
        # Countdown timer frame
        self.countdown_frame = ttk.LabelFrame(clock_frame, text="⏱️ Countdown Timer", padding="10")
        self.countdown_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(self.countdown_frame, text="Count down to your event!", 
                 font=('TkDefaultFont', 9, 'italic')).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # Event name
        ttk.Label(self.countdown_frame, text="Event Name:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.countdown_event_var = tk.StringVar(value="Event")
        ttk.Entry(self.countdown_frame, textvariable=self.countdown_event_var, width=40).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Target date and time
        ttk.Label(self.countdown_frame, text="Target Date:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        
        date_frame = ttk.Frame(self.countdown_frame)
        date_frame.grid(row=2, column=1, sticky=tk.W, pady=(0, 5))
        
        ttk.Label(date_frame, text="Year:").pack(side=tk.LEFT, padx=(0, 5))
        self.countdown_year_var = tk.IntVar(value=2026)
        ttk.Spinbox(date_frame, from_=2026, to=2099, textvariable=self.countdown_year_var, width=6).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(date_frame, text="Month:").pack(side=tk.LEFT, padx=(0, 5))
        self.countdown_month_var = tk.IntVar(value=1)
        ttk.Spinbox(date_frame, from_=1, to=12, textvariable=self.countdown_month_var, width=4).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(date_frame, text="Day:").pack(side=tk.LEFT, padx=(0, 5))
        self.countdown_day_var = tk.IntVar(value=1)
        ttk.Spinbox(date_frame, from_=1, to=31, textvariable=self.countdown_day_var, width=4).pack(side=tk.LEFT)
        
        # Target time
        ttk.Label(self.countdown_frame, text="Target Time:").grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        
        time_frame = ttk.Frame(self.countdown_frame)
        time_frame.grid(row=3, column=1, sticky=tk.W, pady=(0, 5))
        
        ttk.Label(time_frame, text="Hour:").pack(side=tk.LEFT, padx=(0, 5))
        self.countdown_hour_var = tk.IntVar(value=0)
        ttk.Spinbox(time_frame, from_=0, to=23, textvariable=self.countdown_hour_var, width=4).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(time_frame, text="Minute:").pack(side=tk.LEFT, padx=(0, 5))
        self.countdown_minute_var = tk.IntVar(value=0)
        ttk.Spinbox(time_frame, from_=0, to=59, textvariable=self.countdown_minute_var, width=4).pack(side=tk.LEFT)
        
        # Display format
        ttk.Label(self.countdown_frame, text="Display Format:").grid(row=4, column=0, sticky=tk.W, pady=(10, 5))
        
        self.countdown_format_var = tk.StringVar(value="days_hours_mins")
        
        format_options = [
            ("Days, Hours, Minutes (123d 5h 30m)", "days_hours_mins"),
            ("Days and Hours (123d 5h)", "days_hours"),
            ("Total Hours and Minutes (2965h 30m)", "hours_mins"),
            ("Days only (123 days)", "days_only"),
            ("With event name (Event: 123d 5h 30m)", "with_name"),
        ]
        
        for i, (label, value) in enumerate(format_options):
            ttk.Radiobutton(self.countdown_frame, text=label, variable=self.countdown_format_var, 
                          value=value).grid(row=5+i, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # Countdown colors
        countdown_color_frame = ttk.Frame(self.countdown_frame)
        countdown_color_frame.grid(row=10, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))
        
        ttk.Label(countdown_color_frame, text="Text Color:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.countdown_color = "#00ff00"  # Green default
        self.countdown_color_canvas = tk.Canvas(countdown_color_frame, width=30, height=20, 
                                               bg=self.countdown_color, relief=tk.SUNKEN)
        self.countdown_color_canvas.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(countdown_color_frame, text="Choose", command=self.choose_countdown_color).pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Label(countdown_color_frame, text="Background:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.countdown_bg_color = "#000000"
        self.countdown_bg_color_canvas = tk.Canvas(countdown_color_frame, width=30, height=20, 
                                                   bg=self.countdown_bg_color, relief=tk.SUNKEN)
        self.countdown_bg_color_canvas.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(countdown_color_frame, text="Choose", command=self.choose_countdown_bg_color).pack(side=tk.LEFT)
        
        # Countdown animation
        countdown_anim_frame = ttk.Frame(self.countdown_frame)
        countdown_anim_frame.grid(row=11, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        ttk.Label(countdown_anim_frame, text="Animation:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.countdown_animation_var = tk.StringVar(value="static")
        
        for anim in ["Static", "Scroll Left", "Flash"]:
            ttk.Radiobutton(countdown_anim_frame, text=anim, variable=self.countdown_animation_var, 
                          value=anim.lower().replace(" ", "_")).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(countdown_anim_frame, text="Speed:").pack(side=tk.LEFT, padx=(15, 5))
        
        self.countdown_speed_var = tk.IntVar(value=50)
        ttk.Spinbox(countdown_anim_frame, from_=1, to=100, textvariable=self.countdown_speed_var, 
                   width=5).pack(side=tk.LEFT)
        
        # Update interval
        countdown_interval_frame = ttk.Frame(self.countdown_frame)
        countdown_interval_frame.grid(row=12, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        ttk.Label(countdown_interval_frame, text="Update every:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.countdown_update_interval_var = tk.IntVar(value=60)
        ttk.Spinbox(countdown_interval_frame, from_=1, to=3600, textvariable=self.countdown_update_interval_var, 
                   width=5).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(countdown_interval_frame, text="second(s)").pack(side=tk.LEFT)
        
        # Send buttons
        button_frame = ttk.Frame(clock_frame)
        button_frame.pack(pady=(10, 0))
        
        self.send_clock_btn = ttk.Button(button_frame, text="Show Clock", 
                                         command=self.show_clock, state=tk.DISABLED)
        self.send_clock_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_clock_btn = ttk.Button(button_frame, text="Stop Live Clock", 
                                         command=self.stop_live_clock, state=tk.DISABLED)
        self.stop_clock_btn.pack(side=tk.LEFT)
        
        # Initialize clock update timer
        self.clock_timer = None
        self.clock_running = False
        
        # Update initial visibility
        self.update_clock_options()
        
    def create_settings_tab(self):
        """Create the settings control tab"""
        settings_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(settings_frame, text="Settings")
        
        # Brightness
        ttk.Label(settings_frame, text="Brightness:").grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        self.brightness_var = tk.IntVar(value=50)
        brightness_frame = ttk.Frame(settings_frame)
        brightness_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Scale(brightness_frame, from_=1, to=100, variable=self.brightness_var, orient=tk.HORIZONTAL, length=300).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(brightness_frame, textvariable=self.brightness_var).pack(side=tk.LEFT)
        
        self.set_brightness_btn = ttk.Button(settings_frame, text="Set Brightness", command=self.set_brightness, state=tk.DISABLED)
        self.set_brightness_btn.grid(row=1, column=0, columnspan=2, pady=(0, 20))
        
        # Power control
        ttk.Label(settings_frame, text="Power Control:").grid(row=2, column=0, sticky=tk.W, pady=(0, 10))
        
        power_frame = ttk.Frame(settings_frame)
        power_frame.grid(row=2, column=1, sticky=tk.W, pady=(0, 10))
        
        self.power_on_btn = ttk.Button(power_frame, text="Power ON", command=lambda: self.set_power(True), state=tk.DISABLED)
        self.power_on_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.power_off_btn = ttk.Button(power_frame, text="Power OFF", command=lambda: self.set_power(False), state=tk.DISABLED)
        self.power_off_btn.pack(side=tk.LEFT)
        
    def start_event_loop(self):
        """Start asyncio event loop in a separate thread"""
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()
        
        thread = threading.Thread(target=run_loop, daemon=True)
        thread.start()
        
    def run_async(self, coro):
        """Run an async coroutine in the event loop"""
        if self.loop:
            future = asyncio.run_coroutine_threadsafe(coro, self.loop)
            return future.result(timeout=30)
        
    def scan_devices(self):
        """Scan for Bluetooth LE devices"""
        self.scan_btn.config(state=tk.DISABLED, text="Scanning...")
        self.device_combo['values'] = []
        
        def scan_task():
            try:
                devices = self.run_async(self._scan_devices())
                
                # Update UI in main thread
                self.root.after(0, lambda: self._update_device_list(devices))
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: messagebox.showerror("Scan Error", f"Failed to scan: {error_msg}"))
            finally:
                self.root.after(0, lambda: self.scan_btn.config(state=tk.NORMAL, text="Scan"))
        
        threading.Thread(target=scan_task, daemon=True).start()
    
    async def _scan_devices(self):
        """Async method to scan for devices"""
        devices = await BleakScanner.discover(timeout=5.0)
        # Filter for LED devices
        ipixel_devices = {}
        for device in devices:
            if device.name and ("LED" in device.name or "BLE" in device.name or "iPixel" in device.name):
                ipixel_devices[f"{device.name} ({device.address})"] = device.address
        return ipixel_devices
    
    def _update_device_list(self, devices):
        """Update the device list in the UI"""
        if devices:
            self.device_combo['values'] = list(devices.keys())
            self.device_combo.current(0)
            self.devices_dict = devices
    
    def toggle_connection(self):
        """Connect or disconnect from device"""
        if not self.is_connected:
            self.connect_device()
        else:
            self.disconnect_device()
    
    def connect_device(self):
        """Connect to the selected device"""
        device_str = self.device_var.get()
        if not device_str:
            messagebox.showwarning("No Device", "Please scan and select a device first")
            return
        
        self.device_address = self.devices_dict.get(device_str)
        if not self.device_address:
            messagebox.showerror("Error", "Device address not found")
            return
        
        self.connect_btn.config(state=tk.DISABLED, text="Connecting...")
        
        def connect_task():
            try:
                # Create client - this may handle connection internally
                self.client = Client(self.device_address)
                
                # Try to connect if method exists and is callable
                if hasattr(self.client, 'connect') and callable(self.client.connect):
                    self.client.connect()
                
                # Update UI
                self.root.after(0, self._on_connected)
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: self._on_connection_error(error_msg))
        
        threading.Thread(target=connect_task, daemon=True).start()
    
    def _on_connected(self):
        """Called when successfully connected"""
        self.is_connected = True
        
        # Save device address for auto-connect
        self.settings['last_device'] = self.device_address
        self.save_settings()
        
        # Try to get device info
        device_info_text = "Connected"
        try:
            if hasattr(self.client, 'device_info') and self.client.device_info:
                info = self.client.device_info
                if hasattr(info, 'width') and hasattr(info, 'height'):
                    device_info_text = f"Connected - Resolution: {info.width}x{info.height}px"
        except:
            pass
        
        self.status_label.config(text=device_info_text, foreground="green")
        self.connect_btn.config(state=tk.NORMAL, text="Disconnect")
        
        # Enable control buttons
        self.send_text_btn.config(state=tk.NORMAL)
        self.send_image_btn.config(state=tk.NORMAL if self.image_path else tk.DISABLED)
        self.send_clock_btn.config(state=tk.NORMAL)
        self.set_brightness_btn.config(state=tk.NORMAL)
        self.power_on_btn.config(state=tk.NORMAL)
        self.power_off_btn.config(state=tk.NORMAL)
    
    def _on_connection_error(self, error):
        """Called when connection fails"""
        self.connect_btn.config(state=tk.NORMAL, text="Connect")
        messagebox.showerror("Connection Error", f"Failed to connect: {error}")
    
    def disconnect_device(self):
        """Disconnect from the device"""
        if self.client:
            try:
                self.run_async(self.client.disconnect())
            except:
                pass
            
        self.is_connected = False
        self.client = None
        self.status_label.config(text="Disconnected", foreground="red")
        self.connect_btn.config(text="Connect")
        
        # Disable control buttons
        self.send_text_btn.config(state=tk.DISABLED)
        self.send_image_btn.config(state=tk.DISABLED)
        self.send_clock_btn.config(state=tk.DISABLED)
        self.set_brightness_btn.config(state=tk.DISABLED)
        self.power_on_btn.config(state=tk.DISABLED)
        self.power_off_btn.config(state=tk.DISABLED)
    
    def choose_text_color(self):
        """Choose text color"""
        color = colorchooser.askcolor(initialcolor=self.text_color)
        if color[1]:
            self.text_color = color[1]
            self.text_color_canvas.config(bg=self.text_color)
    
    def choose_bg_color(self):
        """Choose background color"""
        color = colorchooser.askcolor(initialcolor=self.bg_color)
        if color[1]:
            self.bg_color = color[1]
            self.bg_color_canvas.config(bg=self.bg_color)
    
    def send_text(self):
        """Send text to the display"""
        text = self.text_input.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("No Text", "Please enter text to display")
            return
        
        # Stop any running live clock
        if hasattr(self, 'clock_running') and self.clock_running:
            self.stop_live_clock()
        
        self.send_text_btn.config(state=tk.DISABLED, text="Sending...")
        
        def send_task():
            try:
                # Convert hex colors to hex strings (without #)
                text_color_hex = self.text_color.lstrip('#')
                bg_color_hex = self.bg_color.lstrip('#')
                
                # Invert speed: 1=slowest (100), 100=fastest (1)
                inverted_speed = 101 - self.speed_var.get()
                
                # Call send_text with animation, speed, and rainbow mode parameters
                result = self.client.send_text(
                    text,
                    char_height=self.font_size_var.get(),
                    color=text_color_hex,
                    bg_color=bg_color_hex,
                    animation=self.animation_var.get(),
                    speed=inverted_speed,
                    rainbow_mode=self.rainbow_var.get()
                )
                
                # If it's a coroutine, run it async; otherwise it already executed
                if asyncio.iscoroutine(result):
                    self.run_async(result)
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to send text: {error_msg}"))
            finally:
                self.root.after(0, lambda: self.send_text_btn.config(state=tk.NORMAL, text="Send Text"))
        
        threading.Thread(target=send_task, daemon=True).start()
    
    def load_image(self):
        """Load an image file"""
        filepath = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("All files", "*.*")
            ]
        )
        
        if filepath:
            try:
                # Load and show preview
                img = Image.open(filepath)
                img.thumbnail((200, 200))
                photo = ImageTk.PhotoImage(img)
                
                self.image_preview_label.config(image=photo, text="")
                self.image_preview_label.image = photo  # Keep a reference
                
                self.image_path = filepath
                self.send_image_btn.config(state=tk.NORMAL if self.is_connected else tk.DISABLED)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {str(e)}")
    
    def send_image(self):
        """Send image to the display"""
        if not self.image_path:
            messagebox.showwarning("No Image", "Please load an image first")
            return
        
        # Stop any running live clock
        if hasattr(self, 'clock_running') and self.clock_running:
            self.stop_live_clock()
        
        self.send_image_btn.config(state=tk.DISABLED, text="Sending...")
        
        def send_task():
            try:
                # First, clear any existing display mode
                try:
                    clear_result = self.client.clear()
                    if asyncio.iscoroutine(clear_result):
                        self.run_async(clear_result)
                except:
                    pass  # Clear might not be available
                
                # Send image with save_slot=0 to display immediately
                # Using 'crop' resize method to fill the entire display
                result = self.client.send_image(self.image_path, resize_method='crop', save_slot=0)
                if asyncio.iscoroutine(result):
                    self.run_async(result)
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to send image: {error_msg}"))
            finally:
                self.root.after(0, lambda: self.send_image_btn.config(state=tk.NORMAL, text="Send Image"))
        
        threading.Thread(target=send_task, daemon=True).start()
    
    def update_clock_options(self):
        """Update visibility of clock options based on selected mode"""
        mode = self.clock_mode_var.get()
        
        if mode == "builtin":
            self.builtin_frame.pack(fill=tk.X, pady=(0, 10))
            self.custom_frame.pack_forget()
            self.countdown_frame.pack_forget()
            self.stop_clock_btn.config(state=tk.DISABLED)
        elif mode == "custom":
            self.builtin_frame.pack_forget()
            self.custom_frame.pack(fill=tk.X, pady=(0, 10))
            self.countdown_frame.pack_forget()
        else:  # countdown
            self.builtin_frame.pack_forget()
            self.custom_frame.pack_forget()
            self.countdown_frame.pack(fill=tk.X, pady=(0, 10))
    
    def choose_clock_color(self):
        """Choose clock text color"""
        color = colorchooser.askcolor(title="Choose Clock Text Color", initialcolor=self.clock_color)
        if color[1]:
            self.clock_color = color[1].lower()
            self.clock_color_canvas.config(bg=self.clock_color)
    
    def choose_clock_bg_color(self):
        """Choose clock background color"""
        color = colorchooser.askcolor(title="Choose Clock Background Color", initialcolor=self.clock_bg_color)
        if color[1]:
            self.clock_bg_color = color[1].lower()
            self.clock_bg_color_canvas.config(bg=self.clock_bg_color)
    
    def choose_countdown_color(self):
        """Choose countdown text color"""
        color = colorchooser.askcolor(title="Choose Countdown Text Color", initialcolor=self.countdown_color)
        if color[1]:
            self.countdown_color = color[1].lower()
            self.countdown_color_canvas.config(bg=self.countdown_color)
    
    def choose_countdown_bg_color(self):
        """Choose countdown background color"""
        color = colorchooser.askcolor(title="Choose Countdown Background Color", initialcolor=self.countdown_bg_color)
        if color[1]:
            self.countdown_bg_color = color[1].lower()
            self.countdown_bg_color_canvas.config(bg=self.countdown_bg_color)
    
    def show_clock(self):
        """Show clock on the display"""
        if not self.is_connected:
            messagebox.showwarning("Not Connected", "Connect to device first")
            return
        
        mode = self.clock_mode_var.get()
        
        if mode == "builtin":
            # Use built-in hardware clock
            self.send_clock_btn.config(state=tk.DISABLED, text="Sending...")
            
            def send_task():
                try:
                    result = self.client.set_clock_mode(style=self.clock_style_var.get())
                    if asyncio.iscoroutine(result):
                        self.run_async(result)
                except Exception as e:
                    error_msg = str(e)
                    self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to show clock: {error_msg}"))
                finally:
                    self.root.after(0, lambda: self.send_clock_btn.config(state=tk.NORMAL, text="Show Clock"))
            
            threading.Thread(target=send_task, daemon=True).start()
        elif mode == "custom":
            # Start custom live clock
            self.start_live_clock()
        else:  # countdown
            # Start countdown timer
            self.start_countdown()
    
    def start_live_clock(self):
        """Start a live updating custom clock"""
        import time
        
        # Stop any existing clock
        self.stop_live_clock()
        
        self.send_clock_btn.config(state=tk.DISABLED)
        self.stop_clock_btn.config(state=tk.NORMAL)
        
        # Mark clock as running
        self.clock_running = True
        
        def update_time():
            if not self.clock_running:
                return  # Clock was stopped
            
            try:
                # Get current time
                current_time = time.strftime(self.time_format_var.get())
                
                # Determine animation
                animation = self.clock_animation_var.get()
                anim_map = {
                    "static": 0,
                    "scroll_left": 1,
                    "flash": 4
                }
                
                # Send text with current time
                def send_task():
                    try:
                        # Remove # from hex colors
                        color_hex = self.clock_color.lower().lstrip('#')
                        bg_color_hex = self.clock_bg_color.lower().lstrip('#')
                        
                        result = self.client.send_text(
                            text=current_time,
                            char_height=16,
                            color=color_hex,
                            bg_color=bg_color_hex,
                            animation=anim_map.get(animation, 0),
                            speed=50
                        )
                        
                        if asyncio.iscoroutine(result):
                            self.run_async(result)
                    except Exception as e:
                        error_msg = str(e)
                        self.root.after(0, lambda: messagebox.showerror("Error", f"Clock update failed: {error_msg}"))
                        self.root.after(0, self.stop_live_clock)
                
                threading.Thread(target=send_task, daemon=True).start()
                
                # Schedule next update
                if self.clock_running:
                    interval = self.clock_update_interval_var.get() * 1000  # Convert to milliseconds
                    self.clock_timer = self.root.after(interval, update_time)
                
            except Exception as e:
                messagebox.showerror("Error", f"Clock error: {str(e)}")
                self.stop_live_clock()
        
        # Start the update loop
        update_time()
    
    def stop_live_clock(self):
        """Stop the live clock updates"""
        self.clock_running = False
        
        if self.clock_timer:
            self.root.after_cancel(self.clock_timer)
            self.clock_timer = None
        
        self.send_clock_btn.config(state=tk.NORMAL)
        self.stop_clock_btn.config(state=tk.DISABLED)
    
    def start_countdown(self):
        """Start a countdown timer"""
        from datetime import datetime, timedelta
        
        # Stop any existing clock
        self.stop_live_clock()
        
        self.send_clock_btn.config(state=tk.DISABLED)
        self.stop_clock_btn.config(state=tk.NORMAL)
        
        # Mark clock as running
        self.clock_running = True
        
        # Get target date/time
        try:
            target_datetime = datetime(
                year=self.countdown_year_var.get(),
                month=self.countdown_month_var.get(),
                day=self.countdown_day_var.get(),
                hour=self.countdown_hour_var.get(),
                minute=self.countdown_minute_var.get()
            )
        except ValueError as e:
            messagebox.showerror("Invalid Date", f"Please enter a valid date and time: {str(e)}")
            self.stop_live_clock()
            return
        
        def update_countdown():
            if not self.clock_running:
                return
            
            try:
                now = datetime.now()
                
                # Check if event has passed
                if now >= target_datetime:
                    countdown_text = f"{self.countdown_event_var.get()}: NOW!"
                else:
                    # Calculate time difference
                    delta = target_datetime - now
                    
                    days = delta.days
                    hours, remainder = divmod(delta.seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    
                    # Format based on selection
                    format_choice = self.countdown_format_var.get()
                    
                    if format_choice == "days_hours_mins":
                        countdown_text = f"{days}d {hours}h {minutes}m"
                    elif format_choice == "days_hours":
                        countdown_text = f"{days}d {hours}h"
                    elif format_choice == "hours_mins":
                        total_hours = days * 24 + hours
                        countdown_text = f"{total_hours}h {minutes}m"
                    elif format_choice == "days_only":
                        countdown_text = f"{days} days"
                    elif format_choice == "with_name":
                        event_name = self.countdown_event_var.get()
                        countdown_text = f"{event_name}: {days}d {hours}h {minutes}m"
                    else:
                        countdown_text = f"{days}d {hours}h {minutes}m"
                
                # Determine animation
                animation = self.countdown_animation_var.get()
                anim_map = {
                    "static": 0,
                    "scroll_left": 1,
                    "flash": 4
                }
                
                # Send text with countdown
                def send_task():
                    try:
                        color_hex = self.countdown_color.lower().lstrip('#')
                        bg_color_hex = self.countdown_bg_color.lower().lstrip('#')
                        
                        # Invert speed: 1=slowest (100), 100=fastest (1)
                        inverted_speed = 101 - self.countdown_speed_var.get()
                        
                        result = self.client.send_text(
                            text=countdown_text,
                            char_height=16,
                            color=color_hex,
                            bg_color=bg_color_hex,
                            animation=anim_map.get(animation, 0),
                            speed=inverted_speed
                        )
                        
                        if asyncio.iscoroutine(result):
                            self.run_async(result)
                    except Exception as e:
                        error_msg = str(e)
                        self.root.after(0, lambda: messagebox.showerror("Error", f"Countdown update failed: {error_msg}"))
                        self.root.after(0, self.stop_live_clock)
                
                threading.Thread(target=send_task, daemon=True).start()
                
                # Schedule next update
                if self.clock_running:
                    interval = self.countdown_update_interval_var.get() * 1000
                    self.clock_timer = self.root.after(interval, update_countdown)
            
            except Exception as e:
                messagebox.showerror("Error", f"Countdown error: {str(e)}")
                self.stop_live_clock()
        
        # Start the update loop
        update_countdown()
    
    def set_brightness(self):
        """Set display brightness"""
        self.set_brightness_btn.config(state=tk.DISABLED, text="Setting...")
        
        def send_task():
            try:
                result = self.client.set_brightness(self.brightness_var.get())
                if asyncio.iscoroutine(result):
                    self.run_async(result)
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to set brightness: {error_msg}"))
            finally:
                self.root.after(0, lambda: self.set_brightness_btn.config(state=tk.NORMAL, text="Set Brightness"))
        
        threading.Thread(target=send_task, daemon=True).start()
    
    def set_power(self, state):
        """Set display power state"""
        btn = self.power_on_btn if state else self.power_off_btn
        btn.config(state=tk.DISABLED)
        
        def send_task():
            try:
                result = self.client.set_power(state)
                if asyncio.iscoroutine(result):
                    self.run_async(result)
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to set power: {error_msg}"))
            finally:
                self.root.after(0, lambda: btn.config(state=tk.NORMAL))
        
        threading.Thread(target=send_task, daemon=True).start()
    
    def load_overlay_bg(self):
        """Load background image for overlay"""
        filepath = filedialog.askopenfilename(
            title="Select Background Image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif"),
                ("All files", "*.*")
            ]
        )
        
        if filepath:
            self.overlay_bg_path = filepath
            filename = os.path.basename(filepath)
            self.overlay_bg_label.config(text=filename)
            self.send_overlay_btn.config(state=tk.NORMAL if self.is_connected else tk.DISABLED)
    
    def choose_overlay_text_color(self):
        """Choose overlay text color"""
        color = colorchooser.askcolor(initialcolor=self.overlay_text_color)
        if color[1]:
            self.overlay_text_color = color[1]
            self.overlay_text_color_canvas.config(bg=self.overlay_text_color)
    
    def preview_overlay(self):
        """Preview the text overlay on image"""
        if not self.overlay_bg_path:
            messagebox.showwarning("No Background", "Please load a background image first")
            return
        
        text = self.overlay_text_input.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("No Text", "Please enter text to overlay")
            return
        
        try:
            # Create the overlay image
            overlay_result = self.create_text_overlay(
                self.overlay_bg_path,
                text,
                self.overlay_text_color,
                self.overlay_font_size_var.get(),
                self.overlay_position_var.get(),
                self.overlay_bold_var.get()
            )
            
            # Check if it's animated (list of frames) or static (single image)
            if isinstance(overlay_result, list):
                # It's an animated GIF - show first frame
                self.overlay_preview_image = overlay_result
                preview = overlay_result[0].copy()
                self.overlay_preview_label.config(text=f"Animated GIF ({len(overlay_result)} frames)")
            else:
                # It's a static image
                self.overlay_preview_image = overlay_result
                preview = overlay_result.copy()
                self.overlay_preview_label.config(text="")
            
            # Show preview
            preview.thumbnail((300, 300))
            photo = ImageTk.PhotoImage(preview)
            
            self.overlay_preview_label.config(image=photo)
            self.overlay_preview_label.image = photo
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create preview: {str(e)}")
    
    def create_text_overlay(self, bg_image_path, text, text_color, font_size, position, bold=False):
        """Create an image with text overlaid on background (supports animated GIFs)"""
        # Load background image
        bg_img = Image.open(bg_image_path)
        
        # Check if it's an animated GIF
        is_animated = hasattr(bg_img, 'n_frames') and bg_img.n_frames > 1
        
        if is_animated:
            # Process animated GIF
            frames = []
            try:
                for frame_num in range(bg_img.n_frames):
                    bg_img.seek(frame_num)
                    frame = bg_img.copy()
                    
                    # Process this frame
                    frame = frame.resize((64, 16), Image.Resampling.LANCZOS)
                    if frame.mode != 'RGB':
                        frame = frame.convert('RGB')
                    
                    # Add text overlay
                    frame = self._add_text_to_image(frame, text, text_color, font_size, position, bold)
                    frames.append(frame)
                
                # Save as animated GIF
                return frames  # Return list of frames for GIF
                
            except Exception as e:
                # If something goes wrong, just use first frame
                bg_img.seek(0)
                frame = bg_img.copy()
                frame = frame.resize((64, 16), Image.Resampling.LANCZOS)
                if frame.mode != 'RGB':
                    frame = frame.convert('RGB')
                return self._add_text_to_image(frame, text, text_color, font_size, position, bold)
        else:
            # Static image
            bg_img = bg_img.resize((64, 16), Image.Resampling.LANCZOS)
            if bg_img.mode != 'RGB':
                bg_img = bg_img.convert('RGB')
            return self._add_text_to_image(bg_img, text, text_color, font_size, position, bold)
    
    def _add_text_to_image(self, img, text, text_color, font_size, position, bold=False):
        """Add text overlay to a single image"""
        # Create drawing context
        draw = ImageDraw.Draw(img)
        
        # Try to use better fonts (in order of preference)
        font = None
        font_names = []
        
        if bold:
            font_names = ["arialbd.ttf", "Arial-Bold.ttf", "DejaVuSans-Bold.ttf", "FreeSansBold.ttf"]
        else:
            font_names = ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "FreeSans.ttf"]
        
        # Try each font
        for font_name in font_names:
            try:
                font = ImageFont.truetype(font_name, font_size)
                break
            except:
                continue
        
        # If no TrueType font found, use default
        if font is None:
            font = ImageFont.load_default()
        
        # Convert hex color to RGB
        text_color_rgb = tuple(int(text_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        
        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Calculate position
        x = (64 - text_width) // 2  # Center horizontally
        
        if position == "top":
            y = 1
        elif position == "bottom":
            y = 16 - text_height - 1
        else:  # center
            y = (16 - text_height) // 2
        
        # Draw text
        draw.text((x, y), text, fill=text_color_rgb, font=font)
        
        return img
    
    def send_overlay(self):
        """Send the overlay image to display"""
        if not self.overlay_preview_image:
            messagebox.showwarning("No Preview", "Please preview the overlay first")
            return
        
        # Stop any running live clock
        if hasattr(self, 'clock_running') and self.clock_running:
            self.stop_live_clock()
        
        self.send_overlay_btn.config(state=tk.DISABLED, text="Sending...")
        
        def send_task():
            try:
                # Check if it's animated or static
                is_animated = isinstance(self.overlay_preview_image, list)
                
                if is_animated:
                    # Save as animated GIF
                    with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as tmp:
                        tmp_path = tmp.name
                        frames = self.overlay_preview_image
                        # Save first frame and append others
                        frames[0].save(
                            tmp_path,
                            save_all=True,
                            append_images=frames[1:],
                            duration=100,  # 100ms per frame
                            loop=0  # Loop forever
                        )
                else:
                    # Save as PNG
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                        tmp_path = tmp.name
                        self.overlay_preview_image.save(tmp_path, 'PNG')
                
                # Clear display first
                try:
                    clear_result = self.client.clear()
                    if asyncio.iscoroutine(clear_result):
                        self.run_async(clear_result)
                except:
                    pass
                
                # Send the overlay image
                result = self.client.send_image(tmp_path, resize_method='crop', save_slot=0)
                if asyncio.iscoroutine(result):
                    self.run_async(result)
                
                # Clean up temp file
                try:
                    os.unlink(tmp_path)
                except:
                    pass
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to send overlay: {error_msg}"))
            finally:
                self.root.after(0, lambda: self.send_overlay_btn.config(state=tk.NORMAL, text="Send to Display"))
        
        threading.Thread(target=send_task, daemon=True).start()
    
    # ===== PRESET MANAGEMENT FUNCTIONS =====
    
    def load_presets(self):
        """Load presets from JSON file"""
        try:
            if os.path.exists(self.presets_file):
                with open(self.presets_file, 'r') as f:
                    self.presets = json.load(f)
        except Exception as e:
            print(f"Failed to load presets: {e}")
            self.presets = []
    
    def save_presets(self):
        """Save presets to JSON file"""
        try:
            with open(self.presets_file, 'w') as f:
                json.dump(self.presets, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save presets: {e}")
    
    def load_settings(self):
        """Load app settings from JSON file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Failed to load settings: {e}")
        return {'auto_connect': True, 'restore_last_state': True, 'last_device': None, 'last_preset': None}
    
    def save_settings(self):
        """Save app settings to JSON file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Failed to save settings: {e}")
    
    def auto_connect_to_last_device(self):
        """Automatically connect to the last connected device"""
        last_device = self.settings.get('last_device')
        if not last_device or self.is_connected:
            return
        
        # Set status
        self.status_label.config(text="Auto-connecting to last device...", foreground="blue")
        
        # Start scanning in background
        def scan_and_connect():
            try:
                # Wait for event loop to be ready
                import time
                for _ in range(10):
                    if self.loop and self.loop.is_running():
                        break
                    time.sleep(0.1)
                
                # Scan for devices
                future = asyncio.run_coroutine_threadsafe(self._scan_devices(), self.loop)
                devices = future.result(timeout=10)
                
                # Check if last device is available
                for device_name, device_addr in devices.items():
                    if device_addr == last_device:
                        # Found the device, connect
                        self.root.after(0, lambda: self._auto_connect_found(device_name, device_addr, devices))
                        return
                
                # Device not found
                self.root.after(0, lambda: self.status_label.config(
                    text="Last device not found. Please connect manually.", 
                    foreground="orange"))
            except Exception as e:
                print(f"Auto-connect failed: {e}")
                self.root.after(0, lambda: self.status_label.config(
                    text="Not connected", 
                    foreground="red"))
        
        threading.Thread(target=scan_and_connect, daemon=True).start()
    
    def _auto_connect_found(self, device_name, device_addr, devices):
        """Helper to connect after finding device"""
        self.devices_dict = devices
        self.device_combo['values'] = list(devices.keys())
        
        # Find and select the device in combo
        device_list = list(devices.keys())
        for i, name in enumerate(device_list):
            if devices[name] == device_addr:
                self.device_combo.current(i)
                break
        
        # Connect
        self.connect_device()
    
    def restore_last_state(self):
        """Restore the last displayed content"""
        if not self.is_connected:
            return
        
        last_preset_name = self.settings.get('last_preset')
        if not last_preset_name:
            return
        
        # Find the preset
        preset = next((p for p in self.presets if p['name'] == last_preset_name), None)
        if preset:
            self.execute_preset(preset)
    
    def generate_thumbnail(self, image_path, max_size=(64, 16)):
        """Generate a thumbnail from an image file and return as base64 string"""
        try:
            if not os.path.exists(image_path):
                return None
            
            # Open and resize image
            img = Image.open(image_path)
            
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
            import base64
            from io import BytesIO
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            return img_str
        except Exception as e:
            print(f"Failed to generate thumbnail: {e}")
            return None
    
    def get_preset_preview(self, preset):
        """Generate preview text for a preset"""
        preset_type = preset.get('type', 'unknown')
        
        if preset_type == "text":
            text = preset.get('text', '')
            return text[:15] if len(text) <= 15 else text[:12] + "..."
        elif preset_type == "image":
            return "🖼️ Image"
        elif preset_type == "clock":
            clock_mode = preset.get('clock_mode', 'builtin')
            if clock_mode == 'custom':
                format_preview = preset.get('time_format', '%H:%M:%S')
                import time
                return time.strftime(format_preview)
            elif clock_mode == 'countdown':
                event = preset.get('countdown_event', 'Event')
                return f"⏱️ {event}"
            else:
                return "🕐 Clock"
        return "..."
    
    def get_preset_details(self, preset):
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
        return ""
    
    def refresh_preset_buttons(self):
        """Refresh the preset buttons display"""
        # Clear existing buttons and cache
        for widget in self.presets_scrollable_frame.winfo_children():
            widget.destroy()
        self.thumbnail_cache.clear()
        
        if not self.presets:
            ttk.Label(self.presets_scrollable_frame, 
                     text="No presets saved yet. Use other tabs to create content, then save it as a preset.",
                     foreground="gray").pack(pady=20)
            return
        
        # Create buttons for each preset
        for idx, preset in enumerate(self.presets):
            preset_frame = ttk.Frame(self.presets_scrollable_frame, relief=tk.RIDGE, borderwidth=1)
            preset_frame.pack(fill=tk.X, pady=5, padx=5)
            
            # Get preview info
            preview_text = self.get_preset_preview(preset)
            preset_type = preset.get('type', 'unknown')
            
            # Preview label (left side) - colored background
            preview_frame = tk.Frame(preset_frame, width=128, height=32, bg='black')
            preview_frame.pack(side=tk.LEFT, padx=5, pady=5)
            preview_frame.pack_propagate(False)
            
            # Get colors for preview
            if preset_type == "text":
                fg_color = preset.get('text_color', '#FFFFFF')
                bg_color = preset.get('bg_color', '#000000')
            elif preset_type == "clock":
                clock_mode = preset.get('clock_mode', 'builtin')
                if clock_mode == 'custom':
                    fg_color = preset.get('clock_color', '#00ffff')
                    bg_color = preset.get('clock_bg_color', '#000000')
                elif clock_mode == 'countdown':
                    fg_color = preset.get('countdown_color', '#00ff00')
                    bg_color = preset.get('countdown_bg_color', '#000000')
                else:
                    fg_color = '#FFFFFF'
                    bg_color = '#000000'
            else:  # image
                fg_color = '#FFFFFF'
                bg_color = '#000000'
            
            preview_frame.config(bg=bg_color)
            
            # Check if preset has thumbnail data (for images/gifs)
            thumbnail_data = preset.get('thumbnail')
            if thumbnail_data and preset_type == "image":
                try:
                    # Decode base64 thumbnail and display
                    import base64
                    from io import BytesIO
                    img_data = base64.b64decode(thumbnail_data)
                    img = Image.open(BytesIO(img_data))
                    # Scale up 2x for better visibility
                    img = img.resize((128, 32), Image.Resampling.NEAREST)
                    photo = ImageTk.PhotoImage(img)
                    self.thumbnail_cache[f"thumb_{idx}"] = photo  # Keep reference
                    preview_label = tk.Label(preview_frame, image=photo, bg=bg_color)
                    preview_label.pack(expand=True)
                except Exception as e:
                    print(f"Failed to display thumbnail: {e}")
                    # Fallback to text
                    preview_label = tk.Label(preview_frame, text=preview_text, 
                                            fg=fg_color, bg=bg_color,
                                            font=('Courier', 8, 'bold'), wraplength=120)
                    preview_label.pack(expand=True)
            elif preset_type == "text":
                # Render actual text preview for text presets
                try:
                    text_content = preset.get('text', preview_text)
                    # Create image with text rendered at 64x16 (native resolution)
                    thumb_img = Image.new('RGB', (64, 16), bg_color)
                    draw = ImageDraw.Draw(thumb_img)
                    
                    # Try to load a font, fallback to default
                    try:
                        font = ImageFont.truetype("arial.ttf", 8)
                    except:
                        font = ImageFont.load_default()
                    
                    # Wrap text to fit 64 pixels width
                    words = text_content.split()
                    lines = []
                    current_line = []
                    for word in words:
                        test_line = ' '.join(current_line + [word])
                        bbox = draw.textbbox((0, 0), test_line, font=font)
                        if bbox[2] - bbox[0] <= 62:  # 2px margin
                            current_line.append(word)
                        else:
                            if current_line:
                                lines.append(' '.join(current_line))
                            current_line = [word]
                    if current_line:
                        lines.append(' '.join(current_line))
                    
                    # Limit to 2 lines (16px height)
                    lines = lines[:2]
                    
                    # Draw text centered
                    y_offset = (16 - len(lines) * 8) // 2
                    for i, line in enumerate(lines):
                        bbox = draw.textbbox((0, 0), line, font=font)
                        text_width = bbox[2] - bbox[0]
                        x = (64 - text_width) // 2
                        draw.text((x, y_offset + i * 8), line, fill=fg_color, font=font)
                    
                    # Scale up 2x for better visibility
                    thumb_img = thumb_img.resize((128, 32), Image.Resampling.NEAREST)
                    photo = ImageTk.PhotoImage(thumb_img)
                    self.thumbnail_cache[f"thumb_{idx}"] = photo
                    preview_label = tk.Label(preview_frame, image=photo, bg=bg_color)
                    preview_label.pack(expand=True)
                except Exception as e:
                    print(f"Failed to render text thumbnail: {e}")
                    # Fallback to simple label
                    preview_label = tk.Label(preview_frame, text=preview_text, 
                                            fg=fg_color, bg=bg_color,
                                            font=('Courier', 8, 'bold'), wraplength=120)
                    preview_label.pack(expand=True)
            else:
                # Clock or other presets - use text preview
                preview_label = tk.Label(preview_frame, text=preview_text, 
                                        fg=fg_color, bg=bg_color,
                                        font=('Courier', 8, 'bold'), wraplength=120)
                preview_label.pack(expand=True)
            
            # Info frame (middle)
            info_frame = ttk.Frame(preset_frame)
            info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
            
            # Preset name and type
            name_label = ttk.Label(info_frame, text=preset.get('name', f'Preset {idx+1}'),
                                  font=('TkDefaultFont', 10, 'bold'))
            name_label.pack(anchor=tk.W)
            
            # Type and details
            type_icon = {"text": "📝", "image": "🖼️", "clock": "🕐"}.get(preset_type, "❓")
            details = self.get_preset_details(preset)
            details_label = ttk.Label(info_frame, text=f"{type_icon} {preset_type.upper()}: {details}",
                                     foreground="gray", font=('TkDefaultFont', 8))
            details_label.pack(anchor=tk.W)
            
            # Buttons frame (right side)
            btn_frame = ttk.Frame(preset_frame)
            btn_frame.pack(side=tk.RIGHT, padx=5, pady=5)
            
            # Execute button
            preset_btn = ttk.Button(btn_frame, text="▶️ Execute", width=12,
                                   command=lambda p=preset: self.execute_preset(p))
            preset_btn.pack(side=tk.TOP, pady=(0, 2))
            
            # Delete button
            del_btn = ttk.Button(btn_frame, text="🗑️ Delete", width=12,
                               command=lambda i=idx: self.delete_preset(i))
            del_btn.pack(side=tk.TOP)
    
    def save_current_preset(self):
        """Save current configuration as a preset"""
        # Ask for preset name
        dialog = tk.Toplevel(self.root)
        dialog.title("Save Preset")
        dialog.geometry("400x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Preset Name:").pack(pady=(20, 5))
        name_entry = ttk.Entry(dialog, width=40)
        name_entry.pack(pady=(0, 10))
        name_entry.focus()
        
        # Type selection
        type_frame = ttk.Frame(dialog)
        type_frame.pack(pady=10)
        
        type_var = tk.StringVar(value="text")
        ttk.Label(type_frame, text="Type:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(type_frame, text="Text", variable=type_var, value="text").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(type_frame, text="Image", variable=type_var, value="image").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(type_frame, text="Clock", variable=type_var, value="clock").pack(side=tk.LEFT, padx=5)
        
        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("No Name", "Please enter a preset name")
                return
            
            preset_type = type_var.get()
            preset = {"name": name, "type": preset_type}
            
            if preset_type == "text":
                preset["text"] = self.text_input.get("1.0", tk.END).strip()
                preset["text_color"] = self.text_color
                preset["bg_color"] = self.bg_color
                preset["char_height"] = self.font_size_var.get()
                preset["animation"] = self.animation_var.get()
                preset["speed"] = self.speed_var.get()
                preset["rainbow"] = self.rainbow_var.get()
            elif preset_type == "image":
                preset["image_path"] = self.image_path if hasattr(self, 'image_path') and self.image_path else ""
                # Generate thumbnail for image/gif
                if preset["image_path"] and os.path.exists(preset["image_path"]):
                    thumbnail = self.generate_thumbnail(preset["image_path"])
                    if thumbnail:
                        preset["thumbnail"] = thumbnail
            elif preset_type == "clock":
                # Save both built-in and custom clock settings
                preset["clock_mode"] = self.clock_mode_var.get()
                
                if preset["clock_mode"] == "builtin":
                    preset["clock_style"] = self.clock_style_var.get()
                elif preset["clock_mode"] == "custom":
                    preset["time_format"] = self.time_format_var.get()
                    preset["clock_color"] = self.clock_color
                    preset["clock_bg_color"] = self.clock_bg_color
                    preset["clock_animation"] = self.clock_animation_var.get()
                    preset["clock_update_interval"] = self.clock_update_interval_var.get()
                else:  # countdown
                    preset["countdown_event"] = self.countdown_event_var.get()
                    preset["countdown_year"] = self.countdown_year_var.get()
                    preset["countdown_month"] = self.countdown_month_var.get()
                    preset["countdown_day"] = self.countdown_day_var.get()
                    preset["countdown_hour"] = self.countdown_hour_var.get()
                    preset["countdown_minute"] = self.countdown_minute_var.get()
                    preset["countdown_format"] = self.countdown_format_var.get()
                    preset["countdown_color"] = self.countdown_color
                    preset["countdown_bg_color"] = self.countdown_bg_color
                    preset["countdown_animation"] = self.countdown_animation_var.get()
                    preset["countdown_speed"] = self.countdown_speed_var.get()
                    preset["countdown_update_interval"] = self.countdown_update_interval_var.get()
            
            self.presets.append(preset)
            self.save_presets()
            self.refresh_preset_buttons()
            dialog.destroy()
        
        ttk.Button(dialog, text="Save", command=save).pack(pady=10)
    
    def execute_preset(self, preset):
        """Execute a saved preset"""
        if not self.is_connected:
            messagebox.showwarning("Not Connected", "Please connect to a device first")
            return
        
        # Stop any running live clock first
        if hasattr(self, 'clock_running') and self.clock_running:
            self.stop_live_clock()
        
        # Save as last preset for state restoration
        self.settings['last_preset'] = preset.get('name')
        self.save_settings()
        
        preset_type = preset.get('type')
        
        try:
            if preset_type == "text":
                # Send text with saved settings
                def send_task():
                    try:
                        text = preset.get('text', '')
                        text_color = preset.get('text_color', '#FFFFFF').lstrip('#')
                        bg_color = preset.get('bg_color', '#000000').lstrip('#')
                        
                        # Invert speed: 1=slowest (100), 100=fastest (1)
                        saved_speed = preset.get('speed', 50)
                        inverted_speed = 101 - saved_speed
                        
                        result = self.client.send_text(
                            text,
                            char_height=preset.get('char_height', 16),
                            color=text_color,
                            bg_color=bg_color,
                            animation=preset.get('animation', 0),
                            speed=inverted_speed,
                            rainbow_mode=preset.get('rainbow', 0)
                        )
                        
                        if asyncio.iscoroutine(result):
                            self.run_async(result)
                    except Exception as e:
                        error_msg = str(e)
                        self.root.after(0, lambda: messagebox.showerror("Error", f"Failed: {error_msg}"))
                
                threading.Thread(target=send_task, daemon=True).start()
                
            elif preset_type == "image":
                image_path = preset.get('image_path')
                if image_path and os.path.exists(image_path):
                    def send_task():
                        try:
                            result = self.client.send_image(image_path, resize_method='crop', save_slot=0)
                            if asyncio.iscoroutine(result):
                                self.run_async(result)
                        except Exception as e:
                            error_msg = str(e)
                            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed: {error_msg}"))
                    
                    threading.Thread(target=send_task, daemon=True).start()
                else:
                    messagebox.showwarning("Image Not Found", "The image file for this preset no longer exists")
                    
            elif preset_type == "clock":
                clock_mode = preset.get('clock_mode', 'builtin')
                
                if clock_mode == "builtin":
                    # Built-in hardware clock
                    def send_task():
                        try:
                            result = self.client.set_clock_mode(style=preset.get('clock_style', 0))
                            if asyncio.iscoroutine(result):
                                self.run_async(result)
                        except Exception as e:
                            error_msg = str(e)
                            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed: {error_msg}"))
                    
                    threading.Thread(target=send_task, daemon=True).start()
                    
                elif clock_mode == "custom":
                    # Custom live clock - start it
                    import time
                    
                    time_format = preset.get('time_format', '%H:%M:%S')
                    clock_color = preset.get('clock_color', '#00ffff')
                    clock_bg_color = preset.get('clock_bg_color', '#000000')
                    clock_animation = preset.get('clock_animation', 'static')
                    update_interval = preset.get('clock_update_interval', 1)
                    
                    # Stop any existing clock
                    if hasattr(self, 'clock_running') and self.clock_running:
                        self.stop_live_clock()
                    
                    self.clock_running = True
                    
                    def update_time():
                        if not self.clock_running:
                            return
                        
                        try:
                            current_time = time.strftime(time_format)
                            
                            anim_map = {
                                "static": 0,
                                "scroll_left": 1,
                                "flash": 4
                            }
                            
                            def send_task():
                                try:
                                    color_hex = clock_color.lower().lstrip('#')
                                    bg_color_hex = clock_bg_color.lower().lstrip('#')
                                    
                                    result = self.client.send_text(
                                        text=current_time,
                                        char_height=16,
                                        color=color_hex,
                                        bg_color=bg_color_hex,
                                        animation=anim_map.get(clock_animation, 0),
                                        speed=50
                                    )
                                    
                                    if asyncio.iscoroutine(result):
                                        self.run_async(result)
                                except Exception as e:
                                    error_msg = str(e)
                                    self.root.after(0, lambda: messagebox.showerror("Error", f"Clock update failed: {error_msg}"))
                                    self.clock_running = False
                            
                            threading.Thread(target=send_task, daemon=True).start()
                            
                            if self.clock_running:
                                interval = update_interval * 1000
                                self.clock_timer = self.root.after(interval, update_time)
                        
                        except Exception as e:
                            messagebox.showerror("Error", f"Clock error: {str(e)}")
                            self.clock_running = False
                    
                    update_time()
                    
                else:  # countdown
                    # Start countdown timer
                    from datetime import datetime
                    
                    event_name = preset.get('countdown_event', 'Event')
                    target_year = preset.get('countdown_year', 2026)
                    target_month = preset.get('countdown_month', 1)
                    target_day = preset.get('countdown_day', 1)
                    target_hour = preset.get('countdown_hour', 0)
                    target_minute = preset.get('countdown_minute', 0)
                    countdown_format = preset.get('countdown_format', 'days_hours_mins')
                    countdown_color = preset.get('countdown_color', '#00ff00')
                    countdown_bg_color = preset.get('countdown_bg_color', '#000000')
                    countdown_animation = preset.get('countdown_animation', 'static')
                    countdown_speed = preset.get('countdown_speed', 50)
                    update_interval = preset.get('countdown_update_interval', 60)
                    
                    # Stop any existing clock
                    if hasattr(self, 'clock_running') and self.clock_running:
                        self.stop_live_clock()
                    
                    self.clock_running = True
                    
                    try:
                        target_datetime = datetime(target_year, target_month, target_day, target_hour, target_minute)
                    except ValueError:
                        messagebox.showerror("Invalid Date", "The countdown preset has an invalid date")
                        return
                    
                    def update_countdown():
                        if not self.clock_running:
                            return
                        
                        try:
                            now = datetime.now()
                            
                            if now >= target_datetime:
                                countdown_text = f"{event_name}: NOW!"
                            else:
                                delta = target_datetime - now
                                days = delta.days
                                hours, remainder = divmod(delta.seconds, 3600)
                                minutes, seconds = divmod(remainder, 60)
                                
                                if countdown_format == "days_hours_mins":
                                    countdown_text = f"{days}d {hours}h {minutes}m"
                                elif countdown_format == "days_hours":
                                    countdown_text = f"{days}d {hours}h"
                                elif countdown_format == "hours_mins":
                                    total_hours = days * 24 + hours
                                    countdown_text = f"{total_hours}h {minutes}m"
                                elif countdown_format == "days_only":
                                    countdown_text = f"{days} days"
                                elif countdown_format == "with_name":
                                    countdown_text = f"{event_name}: {days}d {hours}h {minutes}m"
                                else:
                                    countdown_text = f"{days}d {hours}h {minutes}m"
                            
                            anim_map = {
                                "static": 0,
                                "scroll_left": 1,
                                "flash": 4
                            }
                            
                            def send_task():
                                try:
                                    color_hex = countdown_color.lower().lstrip('#')
                                    bg_color_hex = countdown_bg_color.lower().lstrip('#')
                                    
                                    # Invert speed: 1=slowest (100), 100=fastest (1)
                                    inverted_speed = 101 - countdown_speed
                                    
                                    result = self.client.send_text(
                                        text=countdown_text,
                                        char_height=16,
                                        color=color_hex,
                                        bg_color=bg_color_hex,
                                        animation=anim_map.get(countdown_animation, 0),
                                        speed=inverted_speed
                                    )
                                    
                                    if asyncio.iscoroutine(result):
                                        self.run_async(result)
                                except Exception as e:
                                    error_msg = str(e)
                                    self.root.after(0, lambda: messagebox.showerror("Error", f"Countdown update failed: {error_msg}"))
                                    self.clock_running = False
                            
                            threading.Thread(target=send_task, daemon=True).start()
                            
                            if self.clock_running:
                                interval = update_interval * 1000
                                self.clock_timer = self.root.after(interval, update_countdown)
                        
                        except Exception as e:
                            messagebox.showerror("Error", f"Countdown error: {str(e)}")
                            self.clock_running = False
                    
                    update_countdown()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to execute preset: {str(e)}")
    
    def delete_preset(self, index):
        """Delete a preset"""
        if messagebox.askyesno("Delete Preset", f"Delete preset '{self.presets[index]['name']}'?"):
            del self.presets[index]
            self.save_presets()
            self.refresh_preset_buttons()
    
    def import_presets(self):
        """Import presets from a JSON file"""
        filepath = filedialog.askopenfilename(
            title="Import Presets",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filepath:
            try:
                with open(filepath, 'r') as f:
                    imported = json.load(f)
                    if isinstance(imported, list):
                        self.presets.extend(imported)
                        self.save_presets()
                        self.refresh_preset_buttons()
                    else:
                        messagebox.showerror("Error", "Invalid preset file format")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import: {str(e)}")
    
    def export_presets(self):
        """Export presets to a JSON file"""
        if not self.presets:
            messagebox.showwarning("No Presets", "No presets to export")
            return
        
        filepath = filedialog.asksaveasfilename(
            title="Export Presets",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filepath:
            try:
                with open(filepath, 'w') as f:
                    json.dump(self.presets, f, indent=2)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {str(e)}")
    
    def edit_playlist(self):
        """Open dialog to edit playlist"""
        if not self.presets:
            return
        
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Playlist")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Instructions
        ttk.Label(dialog, text="Build your playlist by adding presets with display duration",
                 font=('TkDefaultFont', 9, 'italic')).pack(pady=(10, 5))
        
        # Current playlist
        list_frame = ttk.LabelFrame(dialog, text="Playlist Items", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))
        
        # Listbox with scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        playlist_listbox = tk.Listbox(list_container, height=15)
        list_scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=playlist_listbox.yview)
        playlist_listbox.configure(yscrollcommand=list_scrollbar.set)
        
        playlist_listbox.pack(side="left", fill="both", expand=True)
        list_scrollbar.pack(side="right", fill="y")
        
        def refresh_playlist_display():
            playlist_listbox.delete(0, tk.END)
            for i, item in enumerate(self.playlist):
                preset_name = item['preset_name']
                duration = item['duration']
                playlist_listbox.insert(tk.END, f"{i+1}. {preset_name} ({duration}s)")
        
        refresh_playlist_display()
        
        # Add preset controls
        add_frame = ttk.LabelFrame(dialog, text="Add Preset to Playlist", padding="10")
        add_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        add_controls = ttk.Frame(add_frame)
        add_controls.pack(fill=tk.X)
        
        ttk.Label(add_controls, text="Preset:").pack(side=tk.LEFT, padx=(0, 5))
        
        preset_var = tk.StringVar()
        preset_names = [p['name'] for p in self.presets]
        preset_combo = ttk.Combobox(add_controls, textvariable=preset_var, 
                                    values=preset_names, state='readonly', width=30)
        if preset_names:
            preset_combo.current(0)
        preset_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(add_controls, text="Duration (seconds):").pack(side=tk.LEFT, padx=(0, 5))
        
        duration_var = tk.IntVar(value=10)
        duration_spin = ttk.Spinbox(add_controls, from_=1, to=3600, textvariable=duration_var, width=10)
        duration_spin.pack(side=tk.LEFT, padx=(0, 10))
        
        def add_to_playlist():
            if not preset_var.get():
                return
            self.playlist.append({
                'preset_name': preset_var.get(),
                'duration': duration_var.get()
            })
            refresh_playlist_display()
        
        ttk.Button(add_controls, text="➕ Add", command=add_to_playlist).pack(side=tk.LEFT)
        
        # Playlist controls
        control_frame = ttk.Frame(dialog)
        control_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        def move_up():
            selection = playlist_listbox.curselection()
            if selection and selection[0] > 0:
                idx = selection[0]
                self.playlist[idx], self.playlist[idx-1] = self.playlist[idx-1], self.playlist[idx]
                refresh_playlist_display()
                playlist_listbox.selection_set(idx-1)
        
        def move_down():
            selection = playlist_listbox.curselection()
            if selection and selection[0] < len(self.playlist) - 1:
                idx = selection[0]
                self.playlist[idx], self.playlist[idx+1] = self.playlist[idx+1], self.playlist[idx]
                refresh_playlist_display()
                playlist_listbox.selection_set(idx+1)
        
        def remove_item():
            selection = playlist_listbox.curselection()
            if selection:
                self.playlist.pop(selection[0])
                refresh_playlist_display()
        
        def clear_playlist():
            if messagebox.askyesno("Clear Playlist", "Remove all items from playlist?"):
                self.playlist.clear()
                refresh_playlist_display()
        
        ttk.Button(control_frame, text="⬆️ Move Up", command=move_up).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_frame, text="⬇️ Move Down", command=move_down).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_frame, text="🗑️ Remove", command=remove_item).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_frame, text="Clear All", command=clear_playlist).pack(side=tk.LEFT, padx=(10, 0))
        
        # Done button
        ttk.Button(dialog, text="Done", command=dialog.destroy, width=15).pack(pady=(0, 10))
    
    def play_playlist(self):
        """Start playing the playlist"""
        if not self.playlist:
            return
        
        if not self.is_connected:
            messagebox.showwarning("Not Connected", "Connect to device first")
            return
        
        if self.playlist_running and self.playlist_paused:
            # Resume
            self.playlist_paused = False
            self.playlist_status_var.set(f"Playlist: Playing ({self.playlist_index + 1}/{len(self.playlist)})")
            self.schedule_next_preset()
        else:
            # Start from beginning
            self.playlist_running = True
            self.playlist_paused = False
            self.playlist_index = 0
            self.playlist_status_var.set(f"Playlist: Playing ({self.playlist_index + 1}/{len(self.playlist)})")
            self.play_next_preset()
    
    def pause_playlist(self):
        """Pause the playlist"""
        if self.playlist_running and not self.playlist_paused:
            self.playlist_paused = True
            if self.playlist_timer:
                self.root.after_cancel(self.playlist_timer)
                self.playlist_timer = None
            self.playlist_status_var.set(f"Playlist: Paused ({self.playlist_index + 1}/{len(self.playlist)})")
    
    def stop_playlist(self):
        """Stop the playlist"""
        self.playlist_running = False
        self.playlist_paused = False
        self.playlist_index = 0
        if self.playlist_timer:
            self.root.after_cancel(self.playlist_timer)
            self.playlist_timer = None
        self.playlist_status_var.set("Playlist: Not running")
    
    def play_next_preset(self):
        """Play the current preset in the playlist"""
        if not self.playlist_running or self.playlist_paused:
            return
        
        if self.playlist_index >= len(self.playlist):
            # Loop back to start
            self.playlist_index = 0
        
        item = self.playlist[self.playlist_index]
        preset_name = item['preset_name']
        duration = item['duration']
        
        # Find and execute the preset
        preset = next((p for p in self.presets if p['name'] == preset_name), None)
        if preset:
            self.playlist_status_var.set(f"Playlist: Playing '{preset_name}' ({self.playlist_index + 1}/{len(self.playlist)})")
            threading.Thread(target=self.execute_preset, args=(preset,), daemon=True).start()
            
            # Schedule next preset
            self.schedule_next_preset(duration)
        else:
            # Preset not found, skip to next
            self.playlist_index += 1
            self.play_next_preset()
    
    def schedule_next_preset(self, delay_seconds=None):
        """Schedule the next preset to play"""
        if delay_seconds is None and self.playlist_index < len(self.playlist):
            delay_seconds = self.playlist[self.playlist_index]['duration']
        
        if delay_seconds and self.playlist_running and not self.playlist_paused:
            self.playlist_index += 1
            self.playlist_timer = self.root.after(int(delay_seconds * 1000), self.play_next_preset)
    
    def save_playlist(self):
        """Save current playlist to a file"""
        if not self.playlist:
            messagebox.showwarning("Empty Playlist", "Create a playlist first before saving")
            return
        
        # Ask for playlist name
        dialog = tk.Toplevel(self.root)
        dialog.title("Save Playlist")
        dialog.geometry("400x120")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Playlist Name:").pack(pady=(20, 5))
        name_entry = ttk.Entry(dialog, width=40)
        name_entry.pack(pady=(0, 10))
        name_entry.focus()
        
        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("No Name", "Please enter a playlist name")
                return
            
            # Create playlists directory if it doesn't exist
            playlists_dir = "playlists"
            if not os.path.exists(playlists_dir):
                os.makedirs(playlists_dir)
            
            filename = os.path.join(playlists_dir, f"{name}.json")
            
            try:
                playlist_data = {
                    "name": name,
                    "items": self.playlist
                }
                
                with open(filename, 'w') as f:
                    json.dump(playlist_data, f, indent=2)
                
                self.current_playlist_file = filename
                self.current_playlist_name_var.set(f"📋 {name}")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save playlist: {str(e)}")
        
        ttk.Button(dialog, text="Save", command=save).pack(pady=10)
    
    def load_playlist_dialog(self):
        """Show dialog to select and load a playlist"""
        playlists_dir = "playlists"
        
        # Check if playlists directory exists
        if not os.path.exists(playlists_dir):
            messagebox.showinfo("No Playlists", "No saved playlists found. Create and save a playlist first.")
            return
        
        # Get all playlist files
        playlist_files = [f for f in os.listdir(playlists_dir) if f.endswith('.json')]
        
        if not playlist_files:
            messagebox.showinfo("No Playlists", "No saved playlists found. Create and save a playlist first.")
            return
        
        # Create selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Load Playlist")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Select a playlist to load:", 
                 font=('TkDefaultFont', 10, 'bold')).pack(pady=(10, 5))
        
        # Listbox with scrollbar
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        playlist_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=10)
        playlist_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=playlist_listbox.yview)
        
        # Populate listbox
        for filename in sorted(playlist_files):
            display_name = filename[:-5]  # Remove .json extension
            playlist_listbox.insert(tk.END, display_name)
        
        def load_selected():
            selection = playlist_listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a playlist")
                return
            
            filename = playlist_files[selection[0]]
            filepath = os.path.join(playlists_dir, filename)
            
            try:
                with open(filepath, 'r') as f:
                    playlist_data = json.load(f)
                
                self.playlist = playlist_data.get('items', [])
                self.current_playlist_file = filepath
                self.current_playlist_name_var.set(f"📋 {playlist_data.get('name', filename[:-5])}")
                dialog.destroy()
                messagebox.showinfo("Success", f"Loaded playlist with {len(self.playlist)} item(s)")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load playlist: {str(e)}")
        
        def delete_selected():
            selection = playlist_listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a playlist to delete")
                return
            
            filename = playlist_files[selection[0]]
            display_name = filename[:-5]
            
            if messagebox.askyesno("Confirm Delete", f"Delete playlist '{display_name}'?"):
                try:
                    os.remove(os.path.join(playlists_dir, filename))
                    playlist_listbox.delete(selection[0])
                    playlist_files.pop(selection[0])
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete: {str(e)}")
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=(0, 10))
        
        ttk.Button(btn_frame, text="Load", command=load_selected, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Delete", command=delete_selected, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=5)


def main():
    root = tk.Tk()
    app = iPixelController(root)
    root.mainloop()


if __name__ == "__main__":
    main()
