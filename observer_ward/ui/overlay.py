import tkinter as tk
from tkinter import font as tkfont
import threading
import queue
import time

class Overlay:
    def __init__(self, config):
        self.config = config
        self.root = tk.Tk()
        self.root.title("Observer Ward Overlay")
        
        # Remove window decorations (frameless)
        self.root.overrideredirect(True)
        
        # Keep always on top
        self.root.attributes('-topmost', True)
        
        # Set transparency
        # On Windows, we can use a specific color to be transparent
        self.transparent_color = "#000001" # Almost black
        self.root.attributes('-transparentcolor', self.transparent_color)
        self.root.config(bg=self.transparent_color)
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Position: Bottom-Center
        width = 1000
        height = 200 # Height for subtitles area
        x_pos = (screen_width - width) // 2
        y_pos = screen_height - height - 50 # 50px from bottom
        self.root.geometry(f"{width}x{height}+{x_pos}+{y_pos}")
        
        # Make draggable
        self.root.bind("<Button-1>", self._start_move)
        self.root.bind("<B1-Motion>", self._do_move)
        
        # Queue for thread-safe GUI updates
        
        # Queue for thread-safe GUI updates
        self.queue = queue.Queue()
        
        # UI Elements
        self._setup_ui()
        
        # State
        self.chat_callback = None
        self.is_input_active = False
        self.message_history = [] # Store strings instead of widgets
        
        # Drag state
        self._drag_data = {"x": 0, "y": 0}
        
        # Start update loop
        self.root.after(100, self._process_queue)

    def _setup_ui(self):
        # Custom font
        base_size = 14
        size = int(base_size * (self.config.subtitle_font_size_percent / 100))
        self.text_font = tkfont.Font(family=self.config.subtitle_font_family, size=size, weight="bold")
        
        # Container for messages (bottom aligned)
        self.message_frame = tk.Frame(self.root, bg=self.transparent_color)
        self.message_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=20)
        
        # Message labels will be recreated on update
        self.message_labels = []
        
        # Input field (hidden by default)
        self.input_frame = tk.Frame(self.root, bg="#1a1a1a") # Dark grey background
        self.input_entry = tk.Entry(
            self.input_frame, 
            font=self.text_font, 
            bg="#333333", 
            fg="white", 
            insertbackground="white",
            relief=tk.FLAT
        )
        self.input_entry.pack(fill=tk.X, padx=10, pady=10)
        self.input_entry.bind("<Return>", self._on_submit)
        self.input_entry.bind("<Escape>", self._on_cancel)

        # Throttling state
        self.last_update = 0
        self.update_interval = 0.033 # ~30 FPS

    def _process_queue(self):
        """Check queue for new tasks from other threads"""
        try:
            while True:
                task = self.queue.get_nowait()
                action = task.get("action")
                if action == "comment":
                    self._add_message(task["text"])
                elif action == "input":
                    self._show_input_internal()
                elif action == "settings":
                    self._show_settings_internal()
                self.queue.task_done()
        except queue.Empty:
            pass
        
        self.root.after(100, self._process_queue)

    def _add_message(self, text):
        """Add a message to the history and refresh display"""
        self.message_history.append(text)
        if len(self.message_history) > 3:
            self.message_history.pop(0)
        self._refresh_messages()

    def _refresh_messages(self):
        """Re-render messages from history"""
        # Clear existing labels
        for label in self.message_labels:
            label.destroy()
        self.message_labels.clear()
        
        # Render messages (newest at bottom)
        for i, msg in enumerate(reversed(self.message_history)):
            # Determine color: Newest (index 0) gets primary color, others get past color
            text_color = self.config.subtitle_color if i == 0 else self.config.subtitle_past_color
            
            # Determine background
            bg_color = self.transparent_color
            if self.config.subtitle_bg_opacity > 0:
                bg_color = self.config.subtitle_bg_color

            # Container for this message line
            container = tk.Frame(self.message_frame, bg=bg_color)
            container.pack(side=tk.BOTTOM, fill=tk.X, pady=2)
            self.message_labels.append(container)
            
            # Helper to create label
            def make_label(color, offset_x, offset_y):
                l = tk.Label(
                    container, 
                    text=msg, 
                    font=self.text_font,
                    bg=bg_color, 
                    fg=color, 
                    wraplength=960,
                    justify=tk.CENTER
                )
                l.place(relx=0.5, rely=0.5, anchor=tk.CENTER, x=offset_x, y=offset_y)
                return l

            # Create outline (4 directions)
            outline_color = "black"
            thickness = 2
            make_label(outline_color, -thickness, -thickness)
            make_label(outline_color, thickness, -thickness)
            make_label(outline_color, -thickness, thickness)
            make_label(outline_color, thickness, thickness)
            
            # Main text
            l = tk.Label(
                container, 
                text=msg, 
                font=self.text_font,
                bg=bg_color, 
                fg=text_color, 
                wraplength=960,
                justify=tk.CENTER
            )
            l.pack(side=tk.TOP, pady=thickness) # Pack the main one to define height

    def _start_move(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _do_move(self, event):
        x = self.root.winfo_x() - self._drag_data["x"] + event.x
        y = self.root.winfo_y() - self._drag_data["y"] + event.y
        self.root.geometry(f"+{x}+{y}")

    def _show_input_internal(self):
        if not self.is_input_active:
            self.input_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
            self.input_entry.focus_set()
            self.is_input_active = True

    def _hide_input_internal(self):
        if self.is_input_active:
            self.input_frame.pack_forget()
            self.input_entry.delete(0, tk.END)
            self.is_input_active = False
            self.root.focus_set()

    def _on_submit(self, event):
        text = self.input_entry.get()
        if text and self.chat_callback:
            threading.Thread(target=self.chat_callback, args=(text,)).start()
        self._hide_input_internal()

    def _on_cancel(self, event):
        self._hide_input_internal()

    # --- Public API (Thread-Safe) ---

    def run(self):
        """Start the GUI main loop. BLOCKING."""
        self.root.mainloop()

    def display_comment(self, text):
        """Queue a comment to be displayed"""
        self.queue.put({"action": "comment", "text": text})

    def show_input(self, callback):
        """Queue request to show input"""
        self.chat_callback = callback
        self.queue.put({"action": "input"})

    def show_settings(self):
        """Queue request to show settings"""
        self.queue.put({"action": "settings"})

    def _show_settings_internal(self):
        """Show settings dialog with modern dark UI"""
        # Create a Toplevel window
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Settings")
        settings_win.geometry("400x700")
        settings_win.configure(bg="#1e1e1e")
        settings_win.attributes('-topmost', True)
        
        # Styles
        bg_color = "#1e1e1e"
        fg_color = "#ffffff"
        accent_color = "#4CAF50"
        
        # Header
        header = tk.Label(settings_win, text="Overlay Settings", font=("Segoe UI", 16, "bold"), bg=bg_color, fg=fg_color)
        header.pack(pady=(20, 20))
        
        # Content Frame
        content = tk.Frame(settings_win, bg=bg_color)
        content.pack(fill=tk.BOTH, expand=True, padx=30)
        
        # --- Font Family ---
        tk.Label(content, text="Font Family", font=("Segoe UI", 12), bg=bg_color, fg="#aaaaaa").pack(anchor="w", pady=(0, 5))
        font_var = tk.StringVar(value=self.config.subtitle_font_family)
        fonts = ["Helvetica", "Arial", "Times New Roman", "Courier New", "Segoe UI", "Verdana", "Comic Sans MS"]
        font_menu = tk.OptionMenu(content, font_var, *fonts)
        font_menu.config(bg="#333333", fg="white", highlightthickness=0, relief=tk.FLAT)
        font_menu["menu"].config(bg="#333333", fg="white")
        font_menu.pack(fill=tk.X, pady=(0, 15))

        # --- Font Size (%) ---
        tk.Label(content, text="Font Size (%)", font=("Segoe UI", 12), bg=bg_color, fg="#aaaaaa").pack(anchor="w", pady=(0, 5))
        
        size_var = tk.IntVar(value=self.config.subtitle_font_size_percent)
        scale = tk.Scale(
            content, 
            from_=50, to=200, 
            orient=tk.HORIZONTAL, 
            variable=size_var, 
            bg=bg_color, 
            fg=fg_color,
            highlightthickness=0,
            troughcolor="#333333",
            activebackground=accent_color
        )
        scale.pack(fill=tk.X, pady=(0, 20))
        
        # --- Helper for Color Picker ---
        def create_color_picker(parent, title, current_var, options):
            tk.Label(parent, text=title, font=("Segoe UI", 12), bg=bg_color, fg="#aaaaaa").pack(anchor="w", pady=(0, 5))
            frame = tk.Frame(parent, bg=bg_color)
            frame.pack(anchor="w", pady=(0, 20))
            
            buttons = []
            
            def on_select(selected_color, btn_widget):
                current_var.set(selected_color)
                # Update borders
                for btn in buttons:
                    btn.configure(relief=tk.FLAT, bd=0)
                btn_widget.configure(relief=tk.SOLID, bd=2)
            
            for color in options:
                btn = tk.Frame(frame, bg=color, width=30, height=30, cursor="hand2")
                btn.pack(side=tk.LEFT, padx=5)
                
                # Bind click
                btn.bind("<Button-1>", lambda e, c=color, b=btn: on_select(c, b))
                
                # Initial selection state
                if current_var.get() == color:
                    btn.configure(relief=tk.SOLID, bd=2)
                    
                buttons.append(btn)

        # --- Text Color ---
        color_var = tk.StringVar(value=self.config.subtitle_color)
        create_color_picker(content, "Text Color", color_var, ["white", "yellow", "#00ff00", "#00ffff", "#ff00ff", "#ff5555"])
        
        # --- Past Text Color ---
        past_color_var = tk.StringVar(value=self.config.subtitle_past_color)
        create_color_picker(content, "Past Text Color", past_color_var, ["#cccccc", "#888888", "#aaaaaa", "#666666", "white"])
        
        # --- Background Color ---
        bg_color_var = tk.StringVar(value=self.config.subtitle_bg_color)
        create_color_picker(content, "Background Color", bg_color_var, ["black", "#202020", "#404040", "blue", "red"])

        # --- Background Opacity ---
        tk.Label(content, text="Background Opacity (%)", font=("Segoe UI", 12), bg=bg_color, fg="#aaaaaa").pack(anchor="w", pady=(0, 5))
        opacity_var = tk.IntVar(value=self.config.subtitle_bg_opacity)
        opacity_scale = tk.Scale(
            content, 
            from_=0, to=100, 
            orient=tk.HORIZONTAL, 
            variable=opacity_var, 
            bg=bg_color, 
            fg=fg_color,
            highlightthickness=0,
            troughcolor="#333333",
            activebackground=accent_color
        )
        opacity_scale.pack(fill=tk.X, pady=(0, 20))

        # --- Save Button ---
        def save():
            self.config.subtitle_font_family = font_var.get()
            self.config.subtitle_font_size_percent = size_var.get()
            self.config.subtitle_color = color_var.get()
            self.config.subtitle_past_color = past_color_var.get()
            self.config.subtitle_bg_color = bg_color_var.get()
            self.config.subtitle_bg_opacity = opacity_var.get()
            
            # Update font
            base_size = 14
            size = int(base_size * (self.config.subtitle_font_size_percent / 100))
            self.text_font.configure(family=self.config.subtitle_font_family, size=size)
            
            # Refresh UI
            self._refresh_messages()
            settings_win.destroy()
            
        save_btn = tk.Button(
            settings_win, 
            text="Save Changes", 
            command=save, 
            bg=accent_color, 
            fg="white", 
            font=("Segoe UI", 11, "bold"),
            relief=tk.FLAT,
            padx=20,
            pady=8,
            cursor="hand2"
        )
        save_btn.pack(side=tk.BOTTOM, pady=30)
