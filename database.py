"""
Database module - SQLite database for video metadata and thumbnails.
"""
import sqlite3
import os
import subprocess
from datetime import datetime
from typing import List, Optional, Tuple
from settings import get_settings


class VideoDatabase:
    """SQLite database for managing recorded videos."""
    
    def __init__(self):
        settings = get_settings()
        self.db_path = os.path.join(settings.app_data_dir, "videos.db")
        self.thumbnails_dir = settings.thumbnails_dir
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    filepath TEXT NOT NULL UNIQUE,
                    mode TEXT NOT NULL,
                    duration_seconds REAL,
                    file_size_bytes INTEGER,
                    thumbnail_path TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON videos(created_at DESC)")
            conn.commit()
    
    def add_video(self, filepath: str, mode: str, duration_seconds: float = None) -> int:
        """Add a video to the database and generate thumbnail.
        
        Args:
            filepath: Full path to the video file
            mode: Recording mode ('fulltime' or 'buffer')
            duration_seconds: Video duration in seconds (optional)
        
        Returns:
            The ID of the inserted video
        """
        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
        
        # Generate thumbnail
        thumbnail_path = self._generate_thumbnail(filepath)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO videos (filename, filepath, mode, duration_seconds, file_size_bytes, thumbnail_path)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (filename, filepath, mode, duration_seconds, file_size, thumbnail_path))
            conn.commit()
            return cursor.lastrowid
    
    def _generate_thumbnail(self, video_path: str) -> Optional[str]:
        """Generate a thumbnail for a video using FFmpeg.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Path to the generated thumbnail, or None if failed
        """
        if not os.path.exists(video_path):
            return None
        
        # Create thumbnail filename based on video filename
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        thumbnail_path = os.path.join(self.thumbnails_dir, f"{video_name}.jpg")
        
        try:
            # Extract frame at 1 second, resize to 160x90
            cmd = [
                "ffmpeg",
                "-y",
                "-ss", "1",
                "-i", video_path,
                "-vframes", "1",
                "-vf", "scale=160:90",
                "-q:v", "5",
                thumbnail_path
            ]
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=10
            )
            
            if os.path.exists(thumbnail_path):
                return thumbnail_path
        except Exception as e:
            print(f"Error generating thumbnail: {e}")
        
        return None
    
    def get_videos(self) -> List[Tuple]:
        """Get all videos sorted by creation date (newest first).
        
        Returns:
            List of tuples: (id, filename, filepath, mode, duration, size, thumbnail, created_at)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, filename, filepath, mode, duration_seconds, 
                       file_size_bytes, thumbnail_path, created_at
                FROM videos
                ORDER BY created_at DESC
            """)
            return cursor.fetchall()
    
    def get_video(self, video_id: int) -> Optional[Tuple]:
        """Get a single video by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, filename, filepath, mode, duration_seconds,
                       file_size_bytes, thumbnail_path, created_at
                FROM videos WHERE id = ?
            """, (video_id,))
            return cursor.fetchone()
    
    def delete_video(self, video_id: int, delete_file: bool = False):
        """Delete a video from the database.
        
        Args:
            video_id: ID of the video to delete
            delete_file: If True, also delete the video file and thumbnail
        """
        if delete_file:
            video = self.get_video(video_id)
            if video:
                filepath = video[2]
                thumbnail = video[6]
                
                # Delete video file
                if filepath and os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except:
                        pass
                
                # Delete thumbnail
                if thumbnail and os.path.exists(thumbnail):
                    try:
                        os.remove(thumbnail)
                    except:
                        pass
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))
            conn.commit()
    
    def video_exists(self, filepath: str) -> bool:
        """Check if a video already exists in the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM videos WHERE filepath = ?", (filepath,)
            )
            return cursor.fetchone() is not None


# Global database instance
_db_instance = None

def get_database() -> VideoDatabase:
    """Get the global database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = VideoDatabase()
    return _db_instance
