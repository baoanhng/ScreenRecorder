"""
Videos Tab - Displays recorded videos with thumbnails.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import os
from PIL import Image, ImageTk
from database import get_database


class VideosTab(ttk.Frame):
    """Tab for viewing and managing recorded videos."""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.thumbnails = {}  # Keep references to prevent garbage collection
        self.video_frames = {}  # Map video_id to frame
        self.videos_data = []  # Store video tuples
        self._create_widgets()
        self.refresh()
    
    def _create_widgets(self):
        """Create the video list UI."""
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(toolbar, text="🔄 Refresh", command=self.refresh).pack(side="left")
        ttk.Button(toolbar, text="🗑️ Delete", command=self._delete_selected).pack(side="left", padx=5)
        ttk.Button(toolbar, text="📂 Open Folder", command=self._open_folder).pack(side="left")
        
        # Create scrollable container
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Canvas for scrolling
        self.canvas = tk.Canvas(container, bg="#1a1a2e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        
        # Inner frame for video cards
        self.inner_frame = tk.Frame(self.canvas, bg="#1a1a2e")
        
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Create window in canvas
        self.canvas_window_id = self.canvas.create_window(0, 0, window=self.inner_frame, anchor="nw")
        
        # Bind events
        self.inner_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        self.selected_id = None
    
    def _on_frame_configure(self, event):
        """Update scroll region when inner frame changes."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _on_canvas_configure(self, event):
        """Update inner frame width when canvas resizes."""
        self.canvas.itemconfig(self.canvas_window_id, width=event.width)
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def refresh(self):
        """Refresh the video list from database."""
        # Clear existing
        for widget in self.inner_frame.winfo_children():
            widget.destroy()
        self.video_frames.clear()
        self.thumbnails.clear()
        self.selected_id = None
        
        db = get_database()
        self.videos_data = db.get_videos() or []
        
        if not self.videos_data:
            empty_label = tk.Label(
                self.inner_frame,
                text="No recordings yet.\n\nPress F9 for fulltime recording\nPress F10 for buffer mode",
                font=("Segoe UI", 11),
                bg="#1a1a2e", fg="#888888",
                justify="center"
            )
            empty_label.pack(pady=50, padx=20)
            return
        
        for video in self.videos_data:
            self._create_video_card(video)
    
    def _create_video_card(self, video):
        """Create a card for a single video."""
        video_id, filename, filepath, mode, duration, size, thumbnail_path, created_at = video
        
        # Outer container (for selection border)
        outer = tk.Frame(self.inner_frame, bg="#1a1a2e", padx=3, pady=3)
        outer.pack(fill="x", padx=5, pady=2)
        outer.video_id = video_id
        outer.filepath = filepath
        self.video_frames[video_id] = outer
        
        # Card background
        card = tk.Frame(outer, bg="#16213e", padx=10, pady=8)
        card.pack(fill="x")
        
        # Bind click events to all widgets
        def bind_clicks(widget):
            widget.bind("<Button-1>", lambda e: self._select_video(video_id))
            widget.bind("<Double-Button-1>", lambda e: self._play_video(filepath))
        
        bind_clicks(outer)
        bind_clicks(card)
        
        # Left side: Thumbnail
        thumb_container = tk.Frame(card, bg="#16213e", width=160, height=90)
        thumb_container.pack(side="left", padx=(0, 15))
        thumb_container.pack_propagate(False)  # Fixed size
        
        thumb_label = tk.Label(thumb_container, bg="#0a0a15", fg="#666666")
        thumb_label.pack(fill="both", expand=True)
        bind_clicks(thumb_label)
        
        # Load thumbnail
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                img = Image.open(thumbnail_path)
                # Don't resize if already correct size
                if img.size != (160, 90):
                    img = img.resize((160, 90), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.thumbnails[video_id] = photo
                thumb_label.configure(image=photo)
            except Exception as e:
                print(f"Thumbnail error for {filename}: {e}")
                thumb_label.configure(text="No Preview")
        else:
            thumb_label.configure(text="No Preview")
        
        # Right side: Info
        info = tk.Frame(card, bg="#16213e")
        info.pack(side="left", fill="both", expand=True)
        bind_clicks(info)
        
        # Filename
        name_label = tk.Label(info, text=filename, font=("Segoe UI", 11, "bold"),
                              bg="#16213e", fg="#eaeaea", anchor="w")
        name_label.pack(anchor="w", fill="x")
        bind_clicks(name_label)
        
        # Mode
        mode_text = "🔴 Fulltime" if mode == "fulltime" else "🔵 Buffer"
        mode_label = tk.Label(info, text=mode_text, font=("Segoe UI", 9),
                              bg="#16213e", fg="#aaaaaa", anchor="w")
        mode_label.pack(anchor="w")
        
        # Metadata
        size_mb = size / (1024 * 1024) if size else 0
        date_str = created_at[:16] if created_at else "Unknown"
        meta_text = f"{size_mb:.1f} MB  •  {date_str}"
        meta_label = tk.Label(info, text=meta_text, font=("Segoe UI", 9),
                              bg="#16213e", fg="#666666", anchor="w")
        meta_label.pack(anchor="w")
    
    def _select_video(self, video_id):
        """Select a video with visual feedback."""
        # Deselect previous
        if self.selected_id in self.video_frames:
            self.video_frames[self.selected_id].configure(bg="#1a1a2e")
        
        # Select new
        self.selected_id = video_id
        if video_id in self.video_frames:
            self.video_frames[video_id].configure(bg="#e94560")  # Red highlight
    
    def _play_video(self, filepath):
        """Open video in default player."""
        if filepath and os.path.exists(filepath):
            os.startfile(filepath)
        else:
            messagebox.showerror("Error", "Video file not found.")
    
    def _open_folder(self):
        """Open the recordings folder."""
        from settings import get_settings
        folder = get_settings().output_dir
        if os.path.exists(folder):
            os.startfile(folder)
        else:
            messagebox.showinfo("Info", "Recordings folder does not exist yet.")
    
    def _delete_selected(self):
        """Delete the selected video."""
        if self.selected_id is None:
            messagebox.showinfo("Info", "Please select a video first.")
            return
        
        if messagebox.askyesno("Confirm Delete", "Delete this video and its file?"):
            db = get_database()
            db.delete_video(self.selected_id, delete_file=True)
            self.selected_id = None
            self.refresh()
