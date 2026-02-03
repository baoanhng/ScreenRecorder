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
        self._create_widgets()
        self.refresh()
    
    def _create_widgets(self):
        """Create the video list UI."""
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(toolbar, text="🔄 Refresh", command=self.refresh).pack(side="left")
        ttk.Button(toolbar, text="🗑️ Delete", command=self._delete_selected).pack(side="left", padx=5)
        
        # Create canvas with scrollbar for video cards
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.canvas = tk.Canvas(container, bg="#1a1a2e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Bind canvas resize
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Store video cards for selection
        self.video_cards = []
        self.selected_id = None
    
    def _on_canvas_configure(self, event):
        """Update scrollable frame width when canvas is resized."""
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def refresh(self):
        """Refresh the video list from database."""
        # Clear existing cards
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.video_cards.clear()
        self.thumbnails.clear()
        
        db = get_database()
        videos = db.get_videos()
        
        if not videos:
            label = ttk.Label(
                self.scrollable_frame,
                text="No recordings yet.\nPress F9 for fulltime recording or F10 for buffer mode.",
                font=("Segoe UI", 11),
                justify="center"
            )
            label.pack(pady=50)
            return
        
        for video in videos:
            self._create_video_card(video)
    
    def _create_video_card(self, video):
        """Create a card for a single video.
        
        Args:
            video: Tuple (id, filename, filepath, mode, duration, size, thumbnail, created_at)
        """
        video_id, filename, filepath, mode, duration, size, thumbnail_path, created_at = video
        
        # Card frame
        card = ttk.Frame(self.scrollable_frame, style="Card.TFrame")
        card.pack(fill="x", pady=5, padx=5)
        card.video_id = video_id
        card.filepath = filepath
        
        # Make card clickable
        card.bind("<Button-1>", lambda e, vid=video_id: self._select_video(vid))
        card.bind("<Double-Button-1>", lambda e, path=filepath: self._play_video(path))
        
        # Content container
        content = ttk.Frame(card)
        content.pack(fill="x", padx=10, pady=8)
        content.bind("<Button-1>", lambda e, vid=video_id: self._select_video(vid))
        content.bind("<Double-Button-1>", lambda e, path=filepath: self._play_video(path))
        
        # Thumbnail
        thumb_label = ttk.Label(content)
        thumb_label.pack(side="left", padx=(0, 10))
        thumb_label.bind("<Button-1>", lambda e, vid=video_id: self._select_video(vid))
        thumb_label.bind("<Double-Button-1>", lambda e, path=filepath: self._play_video(path))
        
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                img = Image.open(thumbnail_path)
                img = img.resize((160, 90), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.thumbnails[video_id] = photo  # Keep reference
                thumb_label.configure(image=photo)
            except Exception as e:
                thumb_label.configure(text="No Preview", width=20)
        else:
            thumb_label.configure(text="No Preview", width=20)
        
        # Info container
        info = ttk.Frame(content)
        info.pack(side="left", fill="both", expand=True)
        info.bind("<Button-1>", lambda e, vid=video_id: self._select_video(vid))
        info.bind("<Double-Button-1>", lambda e, path=filepath: self._play_video(path))
        
        # Filename
        name_label = ttk.Label(info, text=filename, font=("Segoe UI", 11, "bold"))
        name_label.pack(anchor="w")
        name_label.bind("<Button-1>", lambda e, vid=video_id: self._select_video(vid))
        name_label.bind("<Double-Button-1>", lambda e, path=filepath: self._play_video(path))
        
        # Mode badge
        mode_text = "🔴 Fulltime" if mode == "fulltime" else "🔵 Buffer"
        mode_label = ttk.Label(info, text=mode_text, font=("Segoe UI", 9))
        mode_label.pack(anchor="w")
        
        # Size and date
        size_mb = size / (1024 * 1024) if size else 0
        meta_text = f"{size_mb:.1f} MB • {created_at[:16] if created_at else 'Unknown'}"
        meta_label = ttk.Label(info, text=meta_text, font=("Segoe UI", 9), foreground="gray")
        meta_label.pack(anchor="w")
        
        self.video_cards.append(card)
    
    def _select_video(self, video_id):
        """Select a video card."""
        self.selected_id = video_id
        # Visual feedback could be added here
    
    def _play_video(self, filepath):
        """Open video in default player."""
        if filepath and os.path.exists(filepath):
            os.startfile(filepath)
        else:
            messagebox.showerror("Error", "Video file not found.")
    
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
