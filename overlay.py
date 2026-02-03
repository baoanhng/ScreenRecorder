"""
Overlay module - Creates a small status indicator window in the top-right corner.
Uses SetWindowDisplayAffinity to exclude itself from screen capture.
"""
import tkinter as tk
import ctypes
from ctypes import wintypes

# Constants for SetWindowDisplayAffinity
WDA_EXCLUDEFROMCAPTURE = 0x00000011
WDA_NONE = 0x00000000


class Overlay:
    """A small overlay window that shows recording status."""
    
    def __init__(self, master=None):
        """Initialize overlay.
        
        Args:
            master: Parent Tk window. If None, creates own Tk instance.
        """
        if master is None:
            self.root = tk.Tk()
            self._owns_root = True
        else:
            self.root = tk.Toplevel(master)
            self._owns_root = False
        
        self.root.title("Screen Recorder")
        
        # Window configuration
        self.root.overrideredirect(True)  # Remove window decorations
        self.root.attributes("-topmost", True)  # Always on top
        self.root.attributes("-alpha", 0.85)  # Slight transparency
        
        # Size and position (top-right corner)
        window_width = 120
        window_height = 40
        screen_width = self.root.winfo_screenwidth()
        x_position = screen_width - window_width - 20
        y_position = 20
        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        
        # Background
        self.root.configure(bg="#1a1a2e")
        
        # Status label
        self.status_label = tk.Label(
            self.root,
            text="● IDLE",
            font=("Segoe UI", 12, "bold"),
            fg="#888888",
            bg="#1a1a2e"
        )
        self.status_label.pack(expand=True, fill="both")
        
        # Exclude from capture after window is created
        self.root.after(100, self._set_capture_exclusion)
    
    def _set_capture_exclusion(self):
        """Set window display affinity to exclude from screen capture."""
        try:
            # Define argument types for 64-bit compatibility
            user32 = ctypes.windll.user32
            user32.GetParent.argtypes = [wintypes.HWND]
            user32.GetParent.restype = wintypes.HWND
            user32.GetAncestor.argtypes = [wintypes.HWND, ctypes.c_uint]
            user32.GetAncestor.restype = wintypes.HWND
            user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, ctypes.c_DWORD]
            user32.SetWindowDisplayAffinity.restype = wintypes.BOOL
            
            hwnd = user32.GetParent(self.root.winfo_id())
            if hwnd == 0:
                # Try getting the root window handle differently
                hwnd = self.root.winfo_id()
            
            # Get the actual top-level window
            # GA_ROOT = 2
            hwnd = user32.GetAncestor(hwnd, 2)
            
            result = user32.SetWindowDisplayAffinity(
                hwnd, WDA_EXCLUDEFROMCAPTURE
            )
            if result == 0:
                error = ctypes.get_last_error()
                print(f"Warning: SetWindowDisplayAffinity failed with error {error}")
        except Exception as e:
            print(f"Warning: Could not set capture exclusion: {e}")
    
    def update_status(self, mode: str, is_active: bool):
        """Update the overlay status display.
        
        Args:
            mode: 'fulltime', 'buffer', or 'idle'
            is_active: Whether recording is currently active
        """
        if mode == "idle" or not is_active:
            self.status_label.config(text="● IDLE", fg="#888888")
        elif mode == "fulltime":
            self.status_label.config(text="● REC", fg="#ff4444")
        elif mode == "buffer":
            self.status_label.config(text="● BUF", fg="#44aaff")
    
    def run(self):
        """Start the Tkinter main loop."""
        self.root.mainloop()
    
    def schedule(self, ms: int, callback):
        """Schedule a callback on the main thread."""
        self.root.after(ms, callback)
    
    def quit(self):
        """Close the overlay."""
        if self._owns_root:
            self.root.quit()
        self.root.destroy()
