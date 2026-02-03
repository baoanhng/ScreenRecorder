"""
Recorder module - Handles screen recording using FFmpeg.
Supports two modes:
1. Fulltime: Continuous recording to a file
2. Buffer: Rolling buffer that can be saved on demand
"""
import subprocess
import os
import time
import glob
from datetime import datetime
from settings import get_settings
from database import get_database


class ScreenRecorder:
    """Screen recorder using FFmpeg with fulltime and buffer modes."""
    
    def __init__(self):
        """Initialize the recorder using settings."""
        self.settings = get_settings()
        self.db = get_database()
        
        # State
        self.current_mode = None  # 'fulltime', 'buffer', or None
        self.ffmpeg_process = None
        self.current_output_file = None
        self._buffer_start_time = None
        
        # Segment duration for buffer
        self.segment_duration = 10  # 10-second segments
    
    @property
    def output_dir(self) -> str:
        """Get output directory from settings."""
        return self.settings.output_dir
    
    @property
    def buffer_dir(self) -> str:
        """Get buffer directory."""
        buf_dir = os.path.join(self.settings.app_data_dir, ".buffer")
        os.makedirs(buf_dir, exist_ok=True)
        return buf_dir
    
    @property
    def buffer_duration_seconds(self) -> int:
        """Get buffer duration from settings."""
        return self.settings.buffer_duration_seconds
    
    def _get_timestamp(self) -> str:
        """Get a timestamp string for filenames."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _cleanup_buffer(self):
        """Clean up old buffer files."""
        try:
            for f in glob.glob(os.path.join(self.buffer_dir, "buffer_*.mp4")):
                try:
                    os.remove(f)
                except:
                    pass
            for f in glob.glob(os.path.join(self.buffer_dir, "*.m3u8")):
                try:
                    os.remove(f)
                except:
                    pass
            for f in glob.glob(os.path.join(self.buffer_dir, "*.ts")):
                try:
                    os.remove(f)
                except:
                    pass
        except Exception as e:
            print(f"Warning: Buffer cleanup error: {e}")
    
    def start_fulltime(self) -> bool:
        """Start fulltime recording mode.
        
        Returns:
            True if recording started successfully, False otherwise.
        """
        if self.current_mode is not None:
            return False
        
        self._cleanup_buffer()
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        timestamp = self._get_timestamp()
        self.current_output_file = os.path.join(
            self.output_dir, f"recording_{timestamp}.mp4"
        )
        
        # FFmpeg command for fulltime recording
        cmd = [
            "ffmpeg",
            "-f", "gdigrab",
            "-framerate", "30",
            "-i", "desktop",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-y",
            self.current_output_file
        ]
        
        try:
            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.current_mode = "fulltime"
            return True
        except Exception as e:
            print(f"Error starting fulltime recording: {e}")
            return False
    
    def stop_fulltime(self) -> str:
        """Stop fulltime recording.
        
        Returns:
            Path to the recorded file, or None if not recording.
        """
        if self.current_mode != "fulltime" or self.ffmpeg_process is None:
            return None
        
        output_file = self.current_output_file
        
        try:
            # Send 'q' to gracefully stop FFmpeg
            self.ffmpeg_process.stdin.write(b'q')
            self.ffmpeg_process.stdin.flush()
            self.ffmpeg_process.wait(timeout=5)
        except:
            # Force kill if graceful stop fails
            self.ffmpeg_process.kill()
        
        self.ffmpeg_process = None
        self.current_mode = None
        self.current_output_file = None
        
        # Register to database
        if output_file and os.path.exists(output_file):
            try:
                self.db.add_video(output_file, "fulltime")
            except Exception as e:
                print(f"Error adding to database: {e}")
        
        return output_file
    
    def start_buffer(self) -> bool:
        """Start buffer recording mode.
        
        Returns:
            True if recording started successfully, False otherwise.
        """
        if self.current_mode is not None:
            return False
        
        self._cleanup_buffer()
        
        # Calculate number of segments to keep
        max_segments = self.buffer_duration_seconds // self.segment_duration + 2
        
        # FFmpeg command for segmented recording
        segment_pattern = os.path.join(self.buffer_dir, "buffer_%04d.mp4")
        
        cmd = [
            "ffmpeg",
            "-f", "gdigrab",
            "-framerate", "30",
            "-i", "desktop",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-f", "segment",
            "-segment_time", str(self.segment_duration),
            "-segment_wrap", str(max_segments),
            "-reset_timestamps", "1",
            "-y",
            segment_pattern
        ]
        
        try:
            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.current_mode = "buffer"
            self._buffer_start_time = time.time()
            return True
        except Exception as e:
            print(f"Error starting buffer recording: {e}")
            return False
    
    def save_buffer(self) -> str:
        """Stop buffer recording and save the buffer to a file.
        
        Returns:
            Path to the saved buffer file, or None if not in buffer mode.
        """
        if self.current_mode != "buffer" or self.ffmpeg_process is None:
            return None
        
        # Stop the recording first
        try:
            self.ffmpeg_process.stdin.write(b'q')
            self.ffmpeg_process.stdin.flush()
            self.ffmpeg_process.wait(timeout=5)
        except:
            self.ffmpeg_process.kill()
        
        self.ffmpeg_process = None
        self.current_mode = None
        
        # Find all buffer segments
        segments = sorted(glob.glob(os.path.join(self.buffer_dir, "buffer_*.mp4")))
        
        if not segments:
            return None
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create concat file
        timestamp = self._get_timestamp()
        concat_file = os.path.join(self.buffer_dir, "concat.txt")
        output_file = os.path.join(self.output_dir, f"replay_{timestamp}.mp4")
        
        # Sort segments by modification time to get correct order
        segments.sort(key=lambda x: os.path.getmtime(x))
        
        with open(concat_file, 'w') as f:
            for seg in segments:
                # Use forward slashes for FFmpeg
                f.write(f"file '{seg.replace(os.sep, '/')}'\n")
        
        # Concat segments
        concat_cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            "-y",
            output_file
        ]
        
        try:
            subprocess.run(
                concat_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=60
            )
        except Exception as e:
            print(f"Error concatenating buffer: {e}")
            return None
        finally:
            # Cleanup
            self._cleanup_buffer()
            try:
                os.remove(concat_file)
            except:
                pass
        
        # Register to database
        if output_file and os.path.exists(output_file):
            try:
                self.db.add_video(output_file, "buffer")
            except Exception as e:
                print(f"Error adding to database: {e}")
        
        return output_file
    
    def cancel_buffer(self):
        """Cancel buffer recording without saving."""
        if self.current_mode != "buffer" or self.ffmpeg_process is None:
            return
        
        try:
            self.ffmpeg_process.stdin.write(b'q')
            self.ffmpeg_process.stdin.flush()
            self.ffmpeg_process.wait(timeout=5)
        except:
            self.ffmpeg_process.kill()
        
        self.ffmpeg_process = None
        self.current_mode = None
        self._cleanup_buffer()
    
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self.current_mode is not None
    
    def get_mode(self) -> str:
        """Get current recording mode."""
        return self.current_mode
