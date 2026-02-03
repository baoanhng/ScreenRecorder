"""
Settings Tab - Configure app settings.
"""
import tkinter as tk
from tkinter import ttk, filedialog
from settings import get_settings


class SettingsTab(ttk.Frame):
    """Tab for configuring application settings."""
    
    def __init__(self, parent):
        super().__init__(parent)
        self._create_widgets()
    
    def _create_widgets(self):
        """Create the settings UI."""
        settings = get_settings()
        
        # Main container with padding
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Output Directory
        dir_frame = ttk.LabelFrame(container, text="Output Directory", padding=10)
        dir_frame.pack(fill="x", pady=(0, 15))
        
        self.dir_var = tk.StringVar(value=settings.output_dir)
        dir_entry = ttk.Entry(dir_frame, textvariable=self.dir_var, width=50)
        dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        ttk.Button(dir_frame, text="📁 Browse", command=self._browse_directory).pack(side="left")
        
        # Buffer Duration
        buffer_frame = ttk.LabelFrame(container, text="Buffer Duration", padding=10)
        buffer_frame.pack(fill="x", pady=(0, 15))
        
        ttk.Label(buffer_frame, text="Duration (minutes):").pack(side="left")
        
        self.duration_var = tk.IntVar(value=settings.buffer_duration_minutes)
        duration_spin = ttk.Spinbox(
            buffer_frame,
            from_=1,
            to=30,
            textvariable=self.duration_var,
            width=5
        )
        duration_spin.pack(side="left", padx=10)
        
        ttk.Label(buffer_frame, text="(1-30 minutes)", foreground="gray").pack(side="left")
        
        # Hotkeys info
        hotkeys_frame = ttk.LabelFrame(container, text="Hotkeys", padding=10)
        hotkeys_frame.pack(fill="x", pady=(0, 15))
        
        hotkeys_info = """
        F9 - Toggle fulltime recording (start/stop)
        F10 - Toggle buffer mode (start/save)
        Ctrl+Shift+Q - Quit application
        """
        ttk.Label(hotkeys_frame, text=hotkeys_info.strip(), justify="left").pack(anchor="w")
        
        # Save button
        ttk.Button(
            container,
            text="💾 Save Settings",
            command=self._save_settings,
            style="Accent.TButton"
        ).pack(pady=10)
        
        # Status label
        self.status_label = ttk.Label(container, text="", foreground="green")
        self.status_label.pack()
    
    def _browse_directory(self):
        """Open directory browser."""
        directory = filedialog.askdirectory(
            initialdir=self.dir_var.get(),
            title="Select Output Directory"
        )
        if directory:
            self.dir_var.set(directory)
    
    def _save_settings(self):
        """Save current settings."""
        settings = get_settings()
        
        # Validate and save output directory
        new_dir = self.dir_var.get()
        if new_dir:
            settings.output_dir = new_dir
        
        # Save buffer duration
        duration = self.duration_var.get()
        settings.buffer_duration_minutes = duration
        
        self.status_label.config(text="✓ Settings saved!")
        self.after(2000, lambda: self.status_label.config(text=""))
