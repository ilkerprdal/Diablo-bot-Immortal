import tkinter as tk
from PIL import Image, ImageTk
import mss
import numpy as np

class RegionSelector:
    def __init__(self, callback, on_cancel=None, parent=None):
        self.callback = callback
        self.on_cancel = on_cancel
        if parent:
            self.root = tk.Toplevel(parent)
        else:
            self.root = tk.Toplevel()
        self.root.title("Can Barı Bölgesini Seçin")
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.3)
        self.root.configure(bg='black')
        self.root.overrideredirect(True)
        
        # Mouse tracking
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        self.rect = None
        
        # Canvas for drawing
        self.canvas = tk.Canvas(self.root, highlightthickness=0, bg='black')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Take screenshot
        self.sct = mss.mss()
        monitor = self.sct.monitors[1]  # Primary monitor
        screenshot = self.sct.grab(monitor)
        self.original_img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        
        # Screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate scale factor if image is larger than screen
        img_width, img_height = self.original_img.size
        scale_x = screen_width / img_width
        scale_y = screen_height / img_height
        self.scale = min(scale_x, scale_y, 1.0)  # Don't scale up
        
        if self.scale < 1.0:
            new_width = int(img_width * self.scale)
            new_height = int(img_height * self.scale)
            img = self.original_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        else:
            img = self.original_img
            self.scale = 1.0
        
        self.photo = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        
        # Instructions
        self.canvas.create_text(
            screen_width // 2, 50,
            text="Mouse ile can barını seçin (Sol tık + sürükle, ESC ile iptal)",
            fill="yellow",
            font=("Arial", 16, "bold")
        )
        
        # Bind events
        self.canvas.bind("<Button-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.root.bind("<Escape>", self.cancel)
        
        self.root.focus_force()
        self.root.grab_set()
        
        # Handle window close
        def on_closing():
            if self.on_cancel:
                self.on_cancel()
            self.root.destroy()
        
        self.root.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Wait for window to close
        self.root.wait_window()
    
    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect:
            self.canvas.delete(self.rect)
    
    def on_move_press(self, event):
        if self.start_x and self.start_y:
            if self.rect:
                self.canvas.delete(self.rect)
            self.rect = self.canvas.create_rectangle(
                self.start_x, self.start_y, event.x, event.y,
                outline="yellow", width=3
            )
    
    def on_button_release(self, event):
        if self.start_x and self.start_y:
            self.end_x = event.x
            self.end_y = event.y
            
            # Calculate actual coordinates (accounting for image scaling)
            x1 = min(self.start_x, self.end_x)
            y1 = min(self.start_y, self.end_y)
            x2 = max(self.start_x, self.end_x)
            y2 = max(self.start_y, self.end_y)
            
            # Convert to original image coordinates if scaled
            if self.scale < 1.0:
                x1 = int(x1 / self.scale)
                y1 = int(y1 / self.scale)
                x2 = int(x2 / self.scale)
                y2 = int(y2 / self.scale)
            
            width = x2 - x1
            height = y2 - y1
            
            if width > 10 and height > 5:  # Minimum size check
                self.callback(x1, y1, width, height)
                self.root.destroy()
    
    def cancel(self, event):
        if self.on_cancel:
            self.on_cancel()
        self.root.destroy()

