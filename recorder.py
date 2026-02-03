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
        
        # Detect audio device
        self._audio_device = self._detect_audio_device()
        
        # Detect hardware encoder
        self._hw_encoder = self._detect_hw_encoder()
    
    def _detect_audio_device(self) -> str:
        """Detect available audio capture device.
        
        Returns:
            Name of audio device for FFmpeg, or None if not available.
        """
        try:
            # List DirectShow audio devices
            result = subprocess.run(
                ["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=5
            )
            
            output = result.stderr
            
            # Priority devices for system audio capture
            priority_names = ["Stereo Mix", "What U Hear", "CABLE Output", "Loopback"]
            
            audio_devices = []
            
            # Parse FFmpeg output - look for lines with (audio)
            for line in output.split('\n'):
                if '(audio)' in line and '"' in line:
                    # Extract device name between quotes
                    start = line.find('"') + 1
                    end = line.find('"', start)
                    if start > 0 and end > start:
                        device_name = line[start:end]
                        if device_name and not device_name.startswith("@"):
                            audio_devices.append(device_name)
                            print(f"Found audio device: {device_name}")
            
            # Find best match by priority
            for priority in priority_names:
                for device in audio_devices:
                    if priority.lower() in device.lower():
                        print(f"Selected audio device: {device}")
                        return device
            
            # Return first audio device if any (fallback to mic)
            if audio_devices:
                print(f"Using fallback audio device: {audio_devices[0]}")
                return audio_devices[0]
                
        except Exception as e:
            print(f"Error detecting audio devices: {e}")
        
        print("No audio capture device found - recording without audio")
        return None
    
    def _detect_hw_encoder(self) -> str:
        """Detect available and working hardware encoder.
        
        Returns:
            Encoder name (h264_nvenc, h264_amf, h264_qsv) or libx264 as fallback
        """
        # Candidates in priority order
        hw_encoders = [
            ("h264_nvenc", "NVIDIA"),
            ("h264_amf", "AMD"),
            ("h264_qsv", "Intel"),
        ]
        
        for encoder, name in hw_encoders:
            try:
                # Test if the encoder actually works (driver might be too old)
                # Try to encode 1 frame of blank video
                cmd = [
                    "ffmpeg", 
                    "-f", "lavfi", "-i", "color=c=black:s=128x128", 
                    "-frames:v", "1", 
                    "-c:v", encoder, 
                    "-f", "null", "-"
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=3
                )
                
                if result.returncode == 0:
                    print(f"Verified working {name} hardware encoder: {encoder}")
                    return encoder
                else:
                    print(f"Hardware encoder {encoder} found but failed test (Driver update may be required)")
                    
            except Exception as e:
                print(f"Error testing encoder {encoder}: {e}")
        
        print("Using CPU encoder: libx264 (Optimized for performance)")
        return "libx264"
    
    def _build_ffmpeg_cmd(self, output_path: str, is_segment: bool = False,
                          max_segments: int = None) -> list:
        """Build FFmpeg command with appropriate audio settings.
        
        Args:
            output_path: Output file or pattern path
            is_segment: Whether to use segmented output
            max_segments: Max segments for segment wrap (required if is_segment)
            
        Returns:
            FFmpeg command as list
        """
        cmd = ["ffmpeg"]
        
        # Video input (screen capture at 30 fps - balanced quality/performance)
        cmd.extend(["-f", "gdigrab", "-framerate", "30", "-i", "desktop"])
        
        # Audio input if available
        if self._audio_device:
            cmd.extend(["-f", "dshow", "-i", f"audio={self._audio_device}"])
        
        # Video encoding - use hardware if available
        encoder = self._hw_encoder
        if encoder == "h264_nvenc":
            # NVIDIA NVENC - very low CPU usage
            cmd.extend([
                "-c:v", "h264_nvenc",
                "-preset", "p1",        # Fastest preset
                "-tune", "ll",          # Low latency
                "-rc", "vbr",           # Variable bitrate
                "-cq", "23",            # Quality level
                "-pix_fmt", "yuv420p"
            ])
        elif encoder == "h264_amf":
            # AMD AMF
            cmd.extend([
                "-c:v", "h264_amf",
                "-quality", "speed",
                "-rc", "vbr_latency",
                "-qp_i", "23",
                "-qp_p", "23",
                "-pix_fmt", "yuv420p"
            ])
        elif encoder == "h264_qsv":
            # Intel QuickSync
            cmd.extend([
                "-c:v", "h264_qsv",
                "-preset", "veryfast",
                "-global_quality", "23",
                "-pix_fmt", "nv12"
            ])
        else:
            # CPU fallback
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "23",
                "-pix_fmt", "yuv420p"
            ])
        
        # Audio encoding if we have audio
        if self._audio_device:
            cmd.extend(["-c:a", "aac", "-b:a", "192k"])
        
        # Segmentation options
        if is_segment:
            cmd.extend([
                "-f", "segment",
                "-segment_time", str(self.segment_duration),
                "-segment_wrap", str(max_segments),
                "-reset_timestamps", "1"
            ])
        
        cmd.extend(["-y", output_path])
        return cmd
    
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
        
        # Build FFmpeg command using helper
        cmd = self._build_ffmpeg_cmd(self.current_output_file)
        
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
        
        # Build FFmpeg command using helper
        cmd = self._build_ffmpeg_cmd(segment_pattern, is_segment=True, max_segments=max_segments)
        
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
