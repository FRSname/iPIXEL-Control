"""
Control Board tab for iPIXEL Controller
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os
import json
import base64
from io import BytesIO
from typing import TYPE_CHECKING, List, Dict, Any, Optional

from ui.tabs.base_tab import BaseTab
from utils.logger import get_logger
from utils.preset_filters import filter_presets, get_preset_categories

if TYPE_CHECKING:
    from ipixel_controller import iPixelController

logger = get_logger()


class ControlBoardTab(BaseTab):
    """Tab for managing and launching presets"""
    
    def __init__(self, parent: ttk.Notebook, controller: 'iPixelController'):
        super().__init__(parent, controller, "Control Board")
        self.thumbnail_cache = {}
        self.refresh_preset_buttons()

    def setup_ui(self):
        """Build the control board UI"""
        self.content.columnconfigure(0, weight=1)
        
        # Info
        info_label = ttk.Label(self.content, 
                              text="Quick access to saved presets. Create presets in other tabs and save them here.",
                              font=('TkDefaultFont', 9, 'italic'), wraplength=750)
        info_label.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Search and Filter Section
        search_frame = ttk.LabelFrame(self.content, text="🔍 Search & Filter", padding="5")
        search_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        search_frame.columnconfigure(1, weight=1)
        
        ttk.Label(search_frame, text="Search:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        self.preset_search_var = tk.StringVar()
        self.preset_search_var.trace_add('write', lambda *args: self.refresh_preset_buttons())
        search_entry = ttk.Entry(search_frame, textvariable=self.preset_search_var, width=30)
        search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        ttk.Label(search_frame, text="Category:").grid(row=0, column=2, sticky=tk.W, padx=(10, 5))
        
        self.preset_category_var = tk.StringVar(value='all')
        self.preset_category_combo = ttk.Combobox(search_frame, textvariable=self.preset_category_var, 
                                                   state="readonly", width=15)
        self.preset_category_combo['values'] = ['all']
        self.preset_category_combo.grid(row=0, column=3, sticky=tk.W)
        self.preset_category_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_preset_buttons())
        
        ttk.Button(search_frame, text="Clear", command=self.clear_preset_filter, 
                   width=8).grid(row=0, column=4, padx=(10, 0))
        
        # Preset buttons area
        self.presets_frame = ttk.LabelFrame(self.content, text="Saved Presets", padding="10")
        self.presets_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        self.content.rowconfigure(2, weight=1)
        
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

        # Mousewheel binding
        self.presets_canvas.bind("<Enter>", self._bind_mousewheel)
        self.presets_canvas.bind("<Leave>", self._unbind_mousewheel)
        self.presets_scrollable_frame.bind("<Enter>", self._bind_mousewheel)
        self.presets_scrollable_frame.bind("<Leave>", self._unbind_mousewheel)
        
        # Playlist section
        playlist_frame = ttk.LabelFrame(self.content, text="🎵 Playlist - Auto Switch Presets", padding="10")
        playlist_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 10))
        
        # Playlist controls
        playlist_control_frame = ttk.Frame(playlist_frame)
        playlist_control_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(playlist_control_frame, text="▶️ Play", 
                  command=self.controller.play_playlist, width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(playlist_control_frame, text="⏸️ Pause", 
                  command=self.controller.pause_playlist, width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(playlist_control_frame, text="⏹️ Stop", 
                  command=self.controller.stop_playlist, width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(playlist_control_frame, text="✏️ Edit Playlist", 
                  command=self.controller.edit_playlist, width=15).pack(side=tk.LEFT, padx=(10, 0))
        
        # Playlist management buttons (second row)
        playlist_manage_frame = ttk.Frame(playlist_frame)
        playlist_manage_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(playlist_manage_frame, text="💾 Save Playlist As...", 
                  command=self.controller.save_playlist, width=18).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(playlist_manage_frame, text="📂 Load Playlist", 
                  command=self.controller.load_playlist_dialog, width=18).pack(side=tk.LEFT, padx=(0, 5))
        
        # Bind variables from controller
        self.current_playlist_name_var = self.controller.current_playlist_name_var
        ttk.Label(playlist_manage_frame, textvariable=self.current_playlist_name_var, 
                 font=('TkDefaultFont', 8, 'italic'), foreground='gray').pack(side=tk.LEFT, padx=(10, 0))
        
        self.playlist_status_var = self.controller.playlist_status_var
        ttk.Label(playlist_control_frame, textvariable=self.playlist_status_var, 
                 font=('TkDefaultFont', 9, 'italic')).pack(side=tk.LEFT, padx=(20, 0))
        
        # Action buttons
        action_frame = ttk.Frame(self.content)
        action_frame.grid(row=4, column=0, pady=(10, 0))
        
        ttk.Button(action_frame, text="➕ Save Current as Preset", 
                  command=self.controller.save_current_preset).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_frame, text="📁 Import Presets", 
                  command=self.controller.import_presets).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_frame, text="💾 Export Presets", 
                  command=self.controller.export_presets).pack(side=tk.LEFT)

    def _on_mousewheel(self, event):
        if event.num == 4:
            self.presets_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.presets_canvas.yview_scroll(1, "units")
        else:
            self.presets_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _bind_mousewheel(self, _event=None):
        self.presets_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.presets_canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.presets_canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_mousewheel(self, _event=None):
        self.presets_canvas.unbind_all("<MouseWheel>")
        self.presets_canvas.unbind_all("<Button-4>")
        self.presets_canvas.unbind_all("<Button-5>")

    def clear_preset_filter(self):
        """Clear search query and category filter"""
        self.preset_search_var.set('')
        self.preset_category_var.set('all')
        self.refresh_preset_buttons()

    def refresh_preset_buttons(self):
        """Refresh the preset buttons display"""
        if not hasattr(self, 'presets_scrollable_frame'):
            return
            
        # Clear existing buttons and cache
        for widget in self.presets_scrollable_frame.winfo_children():
            widget.destroy()
        self.thumbnail_cache.clear()
        
        # Update category dropdown with available categories
        presets = self.controller.presets
        categories = get_preset_categories(presets)
        if hasattr(self, 'preset_category_combo'):
            self.preset_category_combo['values'] = categories
        
        # Apply filters
        search_query = self.preset_search_var.get()
        category = self.preset_category_var.get()
        
        filtered_presets = filter_presets(presets, search_query, category)
        
        if not filtered_presets:
            if search_query or category != 'all':
                ttk.Label(self.presets_scrollable_frame, 
                         text=f"No presets found matching your search.\nTry different keywords or clear the filter.",
                         foreground="gray").pack(pady=20)
            else:
                ttk.Label(self.presets_scrollable_frame, 
                         text="No presets saved yet. Use other tabs to create content, then save it as a preset.",
                         foreground="gray").pack(pady=20)
            return
        
        # Create buttons for each filtered preset
        for idx, preset in enumerate(filtered_presets):
            self._create_preset_item(idx, preset)

    def _create_preset_item(self, idx: int, preset: Dict[str, Any]):
        """Create a single preset item in the scrollable list"""
        preset_frame = ttk.Frame(self.presets_scrollable_frame, relief=tk.RIDGE, borderwidth=1)
        preset_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # Get preview info
        preview_text = self.controller.get_preset_preview(preset)
        preset_type = preset.get('type', 'unknown')
        
        # Preview label (left side)
        fg_color, bg_color = self._get_preset_colors(preset, preset_type)
        preview_frame = tk.Frame(preset_frame, width=128, height=32, bg=bg_color)
        preview_frame.pack(side=tk.LEFT, padx=5, pady=5)
        preview_frame.pack_propagate(False)
        
        # Thumbnail rendering
        thumbnail_data = preset.get('thumbnail')
        if thumbnail_data and preset_type == "image":
            self._render_image_thumbnail(preview_frame, thumbnail_data, idx, bg_color, preview_text, fg_color)
        elif preset_type == "text":
            self._render_text_thumbnail(preview_frame, preset, idx, bg_color, preview_text, fg_color)
        else:
            preview_label = tk.Label(preview_frame, text=preview_text, 
                                    fg=fg_color, bg=bg_color,
                                    font=('Courier', 8, 'bold'), wraplength=120)
            preview_label.pack(expand=True)
        
        # Info frame (middle)
        info_frame = ttk.Frame(preset_frame)
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        name_label = ttk.Label(info_frame, text=preset.get('name', f'Preset {idx+1}'),
                              font=('TkDefaultFont', 10, 'bold'))
        name_label.pack(anchor=tk.W)
        
        type_icon = {"text": "📝", "image": "🖼️", "clock": "🕐", "stock": "📈", "youtube": "📺", "weather": "🌤️", "animation": "🎨"}.get(preset_type, "❓")
        details = self.controller.get_preset_details(preset)
        details_label = ttk.Label(info_frame, text=f"{type_icon} {preset_type.upper()}: {details}",
                                 foreground="gray", font=('TkDefaultFont', 8))
        details_label.pack(anchor=tk.W)
        
        # Buttons frame (right side)
        btn_frame = ttk.Frame(preset_frame)
        btn_frame.pack(side=tk.RIGHT, padx=5)
        
        # Find index in main presets list
        main_idx = -1
        for i, p in enumerate(self.controller.presets):
            if p == preset:
                main_idx = i
                break
                
        ttk.Button(btn_frame, text="▶️ Run", width=8,
                  command=lambda i=main_idx: self.controller.execute_preset(i)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🗑️", width=3,
                  command=lambda i=main_idx: self.controller.delete_preset(i)).pack(side=tk.LEFT, padx=2)

    def _get_preset_colors(self, preset: Dict[str, Any], preset_type: str):
        """Determine preview colors for a preset type"""
        if preset_type == "text":
            return preset.get('text_color', '#FFFFFF'), preset.get('bg_color', '#000000')
        elif preset_type == "stock":
            return preset.get('text_color', '#00FF00'), preset.get('bg_color', '#000000')
        elif preset_type in ["youtube", "weather"]:
            return preset.get('text_color', '#FFFFFF'), preset.get('bg_color', '#000000')
        elif preset_type == "clock":
            mode = preset.get('clock_mode', 'builtin')
            if mode == 'custom':
                return preset.get('clock_color', '#00ffff'), preset.get('clock_bg_color', '#000000')
            elif mode == 'countdown':
                return preset.get('countdown_color', '#00ff00'), preset.get('countdown_bg_color', '#000000')
        return '#FFFFFF', '#000000'

    def _render_image_thumbnail(self, parent, data, idx, bg_color, fallback_text, fallback_fg):
        try:
            img_data = base64.b64decode(data)
            img = Image.open(BytesIO(img_data))
            img = img.resize((128, 32), Image.Resampling.NEAREST)
            photo = ImageTk.PhotoImage(img)
            self.thumbnail_cache[f"thumb_{idx}"] = photo
            tk.Label(parent, image=photo, bg=bg_color).pack(expand=True)
        except Exception as e:
            logger.error(f"Failed to display thumbnail: {e}")
            tk.Label(parent, text=fallback_text, fg=fallback_fg, bg=bg_color,
                     font=('Courier', 8, 'bold'), wraplength=120).pack(expand=True)

    def _render_text_thumbnail(self, parent, preset, idx, bg_color, fallback_text, fallback_fg):
        try:
            text_content = preset.get('text', fallback_text)
            thumb_img = Image.new('RGB', (64, 16), bg_color)
            draw = ImageDraw.Draw(thumb_img)
            
            try:
                font = ImageFont.truetype("arial.ttf", 8)
            except:
                font = ImageFont.load_default()
            
            words = text_content.split()
            lines = []
            current_line = []
            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=font)
                if bbox[2] - bbox[0] <= 62:
                    current_line.append(word)
                else:
                    if current_line: lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line: lines.append(' '.join(current_line))
            
            lines = lines[:2]
            y_offset = (16 - len(lines) * 8) // 2
            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                x = (64 - (bbox[2] - bbox[0])) // 2
                draw.text((x, y_offset + i * 8), line, fill=fallback_fg, font=font)
            
            thumb_img = thumb_img.resize((128, 32), Image.Resampling.NEAREST)
            photo = ImageTk.PhotoImage(thumb_img)
            self.thumbnail_cache[f"thumb_text_{idx}"] = photo
            tk.Label(parent, image=photo, bg=bg_color).pack(expand=True)
        except Exception as e:
            logger.error(f"Failed to render text thumbnail: {e}")
            tk.Label(parent, text=fallback_text, fg=fallback_fg, bg=bg_color,
                     font=('Courier', 8, 'bold'), wraplength=120).pack(expand=True)
