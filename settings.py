"""
Settings module - Manages application configuration.
Stores settings in %APPDATA%/ScreenRecorder/config.json
"""
import json
import os
from pathlib import Path
from typing import Any


class Settings:
    """Application settings manager."""
    
    DEFAULT_SETTINGS = {
        "output_dir": str(Path.home() / "Videos" / "ScreenRecorder"),
        "buffer_duration_minutes": 5,  # 1-30 minutes
    }
    
    def __init__(self):
        self.app_data_dir = os.path.join(os.environ.get("APPDATA", str(Path.home())), "ScreenRecorder")
        self.config_file = os.path.join(self.app_data_dir, "config.json")
        self.thumbnails_dir = os.path.join(self.app_data_dir, "thumbnails")
        self._settings = {}
        
        # Ensure directories exist
        os.makedirs(self.app_data_dir, exist_ok=True)
        os.makedirs(self.thumbnails_dir, exist_ok=True)
        
        self._load()
    
    def _load(self):
        """Load settings from file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self._settings = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._settings = {}
        
        # Apply defaults for missing keys
        for key, value in self.DEFAULT_SETTINGS.items():
            if key not in self._settings:
                self._settings[key] = value
        
        # Ensure output directory exists
        os.makedirs(self._settings["output_dir"], exist_ok=True)
    
    def _save(self):
        """Save settings to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self._settings, f, indent=2)
        except IOError as e:
            print(f"Error saving settings: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self._settings.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set a setting value and save."""
        self._settings[key] = value
        self._save()
    
    @property
    def output_dir(self) -> str:
        """Get output directory."""
        return self._settings["output_dir"]
    
    @output_dir.setter
    def output_dir(self, path: str):
        """Set output directory."""
        os.makedirs(path, exist_ok=True)
        self._settings["output_dir"] = path
        self._save()
    
    @property
    def buffer_duration_minutes(self) -> int:
        """Get buffer duration in minutes (1-30)."""
        return self._settings["buffer_duration_minutes"]
    
    @buffer_duration_minutes.setter
    def buffer_duration_minutes(self, minutes: int):
        """Set buffer duration (clamped to 1-30)."""
        self._settings["buffer_duration_minutes"] = max(1, min(30, minutes))
        self._save()
    
    @property
    def buffer_duration_seconds(self) -> int:
        """Get buffer duration in seconds."""
        return self.buffer_duration_minutes * 60


# Global settings instance
_settings_instance = None

def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
