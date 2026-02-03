"""
Main Window - The primary application window with tabs.
Supports minimizing to system tray.
"""
import tkinter as tk
from tkinter import ttk
import threading
from PIL import Image, ImageDraw
import pystray
from ui.videos_tab import VideosTab
from ui.settings_tab import SettingsTab


class MainWindow:
    """Main application window with tabbed interface."""
    
    def __init__(self, recorder, overlay, on_quit_callback=None):
        """Initialize the main window.
        
        Args:
            recorder: ScreenRecorder instance
            overlay: Overlay instance  
            on_quit_callback: Callback when window is closed
        """
        self.recorder = recorder
        self.overlay = overlay
        self.on_quit_callback = on_quit_callback
        
        self.root = tk.Tk()
        self.root.title("Screen Recorder")
        self.root.geometry("700x500")
        self.root.minsize(600, 400)
        
        # System tray
        self.tray_icon = None
        self._tray_thread = None
        
        # Set dark theme
        self._setup_styles()
        
        # Create UI
        self._create_widgets()
        
        # Handle window events
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Unmap>", self._on_minimize)
        
        # Update recording status periodically
        self._update_status()
    
    def _create_tray_icon(self):
        """Create a simple tray icon image."""
        # Create a simple circle icon
        size = 64
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Draw a red circle (recording indicator style)
        draw.ellipse([4, 4, size-4, size-4], fill='#e94560', outline='#1a1a2e', width=2)
        
        return image
    
    def _setup_tray(self):
        """Setup the system tray icon."""
        menu = pystray.Menu(
            pystray.MenuItem("Show", self._show_from_tray, default=True),
            pystray.MenuItem("Fulltime (F9)", self._tray_toggle_fulltime),
            pystray.MenuItem("Buffer (F10)", self._tray_toggle_buffer),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._tray_quit)
        )
        
        self.tray_icon = pystray.Icon(
            "ScreenRecorder",
            self._create_tray_icon(),
            "Screen Recorder",
            menu
        )
    
    def _show_from_tray(self, icon=None, item=None):
        """Show window from tray."""
        self.root.after(0, self._restore_window)
    
    def _restore_window(self):
        """Restore the window."""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        
        # Stop tray icon
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
    
    def _tray_toggle_fulltime(self, icon=None, item=None):
        """Toggle fulltime from tray."""
        self.root.after(0, self._toggle_fulltime)
    
    def _tray_toggle_buffer(self, icon=None, item=None):
        """Toggle buffer from tray."""
        self.root.after(0, self._toggle_buffer)
    
    def _tray_quit(self, icon=None, item=None):
        """Quit from tray."""
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self._on_close)
    
    def _on_minimize(self, event=None):
        """Handle window minimize - send to tray."""
        if self.root.state() == 'iconic':
            self.root.withdraw()  # Hide from taskbar
            self._start_tray()
    
    def _start_tray(self):
        """Start the system tray icon."""
        if self.tray_icon is None:
            self._setup_tray()
            self._tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            self._tray_thread.start()
    
    def _setup_styles(self):
        """Configure ttk styles for dark theme."""
        style = ttk.Style()
        style.theme_use("clam")
        
        # Dark colors
        bg_dark = "#1a1a2e"
        bg_medium = "#16213e"
        fg_light = "#eaeaea"
        accent = "#0f3460"
        
        style.configure(".", background=bg_dark, foreground=fg_light)
        style.configure("TFrame", background=bg_dark)
        style.configure("TLabel", background=bg_dark, foreground=fg_light)
        style.configure("TButton", background=accent, foreground=fg_light)
        style.configure("TNotebook", background=bg_dark)
        style.configure("TNotebook.Tab", background=bg_medium, foreground=fg_light, padding=[15, 8])
        style.map("TNotebook.Tab", background=[("selected", accent)])
        style.configure("Card.TFrame", background=bg_medium)
        style.configure("TLabelframe", background=bg_dark, foreground=fg_light)
        style.configure("TLabelframe.Label", background=bg_dark, foreground=fg_light)
        style.configure("Accent.TButton", background="#e94560", foreground="white")
        
        self.root.configure(bg=bg_dark)
    
    def _create_widgets(self):
        """Create the main window widgets."""
        # Recording controls at top
        controls_frame = ttk.Frame(self.root)
        controls_frame.pack(fill="x", padx=15, pady=15)
        
        # Status indicator
        self.status_label = ttk.Label(
            controls_frame,
            text="● IDLE",
            font=("Segoe UI", 14, "bold"),
            foreground="#888888"
        )
        self.status_label.pack(side="left")
        
        # Recording buttons
        btn_frame = ttk.Frame(controls_frame)
        btn_frame.pack(side="right")
        
        self.fulltime_btn = ttk.Button(
            btn_frame,
            text="🔴 Fulltime (F9)",
            command=self._toggle_fulltime,
            width=18
        )
        self.fulltime_btn.pack(side="left", padx=5)
        
        self.buffer_btn = ttk.Button(
            btn_frame,
            text="🔵 Buffer (F10)",
            command=self._toggle_buffer,
            width=18
        )
        self.buffer_btn.pack(side="left", padx=5)
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Videos tab (default)
        self.videos_tab = VideosTab(self.notebook)
        self.notebook.add(self.videos_tab, text="📹 Videos")
        
        # Settings tab
        self.settings_tab = SettingsTab(self.notebook)
        self.notebook.add(self.settings_tab, text="⚙️ Settings")
    
    def _toggle_fulltime(self):
        """Toggle fulltime recording from UI button."""
        if self.recorder.get_mode() == "fulltime":
            output = self.recorder.stop_fulltime()
            self.overlay.update_status("idle", False)
            if output:
                # Refresh videos list
                self.videos_tab.refresh()
        elif self.recorder.get_mode() is None:
            if self.recorder.start_fulltime():
                self.overlay.update_status("fulltime", True)
    
    def _toggle_buffer(self):
        """Toggle buffer recording from UI button."""
        if self.recorder.get_mode() == "buffer":
            output = self.recorder.save_buffer()
            self.overlay.update_status("idle", False)
            if output:
                self.videos_tab.refresh()
        elif self.recorder.get_mode() is None:
            if self.recorder.start_buffer():
                self.overlay.update_status("buffer", True)
    
    def _update_status(self):
        """Update the status display."""
        mode = self.recorder.get_mode()
        
        if mode == "fulltime":
            self.status_label.config(text="● REC", foreground="#ff4444")
            self.fulltime_btn.config(text="⏹️ Stop (F9)")
            self.buffer_btn.config(state="disabled")
        elif mode == "buffer":
            self.status_label.config(text="● BUF", foreground="#44aaff")
            self.buffer_btn.config(text="💾 Save (F10)")
            self.fulltime_btn.config(state="disabled")
        else:
            self.status_label.config(text="● IDLE", foreground="#888888")
            self.fulltime_btn.config(text="🔴 Fulltime (F9)", state="normal")
            self.buffer_btn.config(text="🔵 Buffer (F10)", state="normal")
        
        # Schedule next update
        self.root.after(500, self._update_status)
    
    def _on_close(self):
        """Handle window close."""
        # Stop tray if running
        if self.tray_icon:
            self.tray_icon.stop()
        
        if self.on_quit_callback:
            self.on_quit_callback()
        self.root.destroy()
    
    def refresh_videos(self):
        """Refresh the videos tab."""
        self.videos_tab.refresh()
    
    def run(self):
        """Start the main loop."""
        self.root.mainloop()
    
    def schedule(self, ms: int, callback):
        """Schedule a callback."""
        self.root.after(ms, callback)
