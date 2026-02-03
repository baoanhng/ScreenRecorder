"""
Screen Recorder - Main entry point
A background screen recorder with overlay and hotkey support.

Hotkeys:
  F9  - Toggle fulltime recording (start/stop)
  F10 - Toggle buffer mode (start buffer / save buffer)
  Ctrl+Shift+Q - Quit application
"""
import keyboard
import sys
from overlay import Overlay
from recorder import ScreenRecorder
from ui.main_window import MainWindow


class ScreenRecorderApp:
    """Main application class that coordinates overlay, recorder, and hotkeys."""
    
    def __init__(self):
        self.recorder = ScreenRecorder()
        
        # Create main window first (it owns the Tk root)
        self.main_window = MainWindow(
            self.recorder,
            overlay=None,  # Will set after creating overlay
            on_quit_callback=self._quit
        )
        
        # Create overlay as Toplevel of main window's root (single Tk instance)
        self.overlay = Overlay(master=self.main_window.root)
        self.main_window.set_overlay(self.overlay)
        
        self._setup_hotkeys()
    
    def _setup_hotkeys(self):
        """Register global hotkeys."""
        keyboard.add_hotkey('F9', self._on_fulltime_hotkey, suppress=True)
        keyboard.add_hotkey('F10', self._on_buffer_hotkey, suppress=True)
        keyboard.add_hotkey('ctrl+shift+q', self._on_quit_hotkey, suppress=True)
    
    def _on_fulltime_hotkey(self):
        """Handle F9 - Toggle fulltime recording."""
        self.main_window.schedule(0, self._toggle_fulltime)
    
    def _on_buffer_hotkey(self):
        """Handle F10 - Toggle buffer mode."""
        self.main_window.schedule(0, self._toggle_buffer)
    
    def _on_quit_hotkey(self):
        """Handle Ctrl+Shift+Q - Quit application."""
        self.main_window.schedule(0, self._quit)
    
    def _toggle_fulltime(self):
        """Toggle fulltime recording mode."""
        if self.recorder.get_mode() == "fulltime":
            output = self.recorder.stop_fulltime()
            self.overlay.update_status("idle", False)
            if output:
                self.main_window.refresh_videos()
        elif self.recorder.get_mode() is None:
            if self.recorder.start_fulltime():
                self.overlay.update_status("fulltime", True)
    
    def _toggle_buffer(self):
        """Toggle buffer recording mode."""
        if self.recorder.get_mode() == "buffer":
            output = self.recorder.save_buffer()
            self.overlay.update_status("idle", False)
            if output:
                self.main_window.refresh_videos()
        elif self.recorder.get_mode() is None:
            if self.recorder.start_buffer():
                self.overlay.update_status("buffer", True)
    
    def _quit(self):
        """Quit the application."""
        # Stop any recording
        if self.recorder.get_mode() == "fulltime":
            self.recorder.stop_fulltime()
        elif self.recorder.get_mode() == "buffer":
            self.recorder.cancel_buffer()
        
        # Cleanup
        keyboard.unhook_all()
        try:
            self.overlay.quit()
        except:
            pass
    
    def run(self):
        """Start the application."""
        print("Screen Recorder started!")
        print("Hotkeys:")
        print("  F9  - Toggle fulltime recording")
        print("  F10 - Toggle buffer mode (saves last N minutes)")
        print("  Ctrl+Shift+Q - Quit")
        print("")
        print(f"Recordings saved to: {self.recorder.output_dir}")
        
        self.overlay.update_status("idle", False)
        
        # Run main window (this is the main loop)
        self.main_window.run()


def main():
    app = ScreenRecorderApp()
    app.run()


if __name__ == "__main__":
    main()
