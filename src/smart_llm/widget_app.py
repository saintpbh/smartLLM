"""Stage 5: Native macOS Floating Glassmorphic Desktop Widget (Tkinter Engine)."""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from datetime import datetime

class SmartLLMDesktopWidget:
    """Native macOS floating, draggable glassmorphic widget using built-in Tkinter."""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = Path(workspace_path).resolve()
        
        self.root = tk.Tk()
        self.root.title("SMART LLM Widget")
        
        # 1. macOS Borderless & Topmost Window Styling
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        # Transparent background trick for macOS window
        self.root.configure(bg="#08090f")
        self.root.attributes("-alpha", 0.90)  # High-quality translucency
        
        # Set exact iOS small widget size
        self.width = 180
        self.height = 180
        
        # Center initially on screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = screen_width - self.width - 50
        y = 100
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        
        # 2. Setup Canvas for Anti-aliased Rounded Corners & Shapes
        self.canvas = tk.Canvas(
            self.root, 
            width=self.width, 
            height=self.height, 
            bg="#08090f", 
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)
        
        # Draw iOS widget rounded box
        self._draw_rounded_bg()
        
        # Draw initial text structures
        self.txt_title = self.canvas.create_text(
            18, 24, text="SMART LLM", anchor="w",
            fill="rgba(255,255,255,0.4)", font=("Outfit", 11, "bold")
        )
        
        # Pulsing LED dot
        self.led = self.canvas.create_oval(
            154, 20, 162, 28, 
            fill="#39ff14", outline="#39ff14"
        )
        
        # Large count number
        self.txt_count = self.canvas.create_text(
            18, 76, text="0", anchor="w",
            fill="#ffffff", font=("Outfit", 42, "bold")
        )
        
        self.txt_label = self.canvas.create_text(
            18, 110, text="지식 모듈 축적됨", anchor="w",
            fill="#8f9bb3", font=("Inter", 10, "medium")
        )
        
        # Footer
        self.txt_footer_lbl = self.canvas.create_text(
            18, 142, text="LATEST ACTIVE EVENT", anchor="w",
            fill="rgba(255,255,255,0.25)", font=("Inter", 8, "bold")
        )
        
        self.txt_footer_val = self.canvas.create_text(
            18, 156, text="WAITING", anchor="w",
            fill="#00d2ff", font=("JetBrains Mono", 8, "bold")
        )
        
        # 3. Draggable Window bindings
        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag_motion)
        
        # Double-click to close widget safely
        self.canvas.bind("<Double-Button-1>", lambda e: self.root.destroy())
        
        # 4. Start real-time update loop
        self.update_widget()

    def _draw_rounded_bg(self):
        """Draw a custom high-quality rounded rectangle matching macOS widget corner radius."""
        r = 28  # Radius
        w = self.width
        h = self.height
        
        # Draw glassmorphic dark container
        self.canvas.create_polygon(
            r, 0, w-r, 0, w, r, w, h-r, w-r, h, r, h, 0, h-r, 0, r,
            fill="#121422", outline="#25293d", width=1.5
        )
        
        # Add smooth arc corners for gorgeous look
        self.canvas.create_arc(0, 0, r*2, r*2, start=90, extent=90, fill="#121422", outline="")
        self.canvas.create_arc(w-r*2, 0, w, r*2, start=0, extent=90, fill="#121422", outline="")
        self.canvas.create_arc(w-r*2, h-r*2, w, h, start=270, extent=90, fill="#121422", outline="")
        self.canvas.create_arc(0, h-r*2, r*2, h, start=180, extent=90, fill="#121422", outline="")

    def start_drag(self, event):
        self.x = event.x
        self.y = event.y

    def drag_motion(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def update_widget(self):
        """Dynamic background polling of index and ledger states."""
        graph_file = self.workspace_path / "smart-llm-out" / "graph.json"
        
        code_nodes = 0
        if graph_file.exists():
            try:
                with open(graph_file, "r", encoding="utf-8") as f:
                    graph_data = json.load(f)
                nodes = graph_data.get("nodes", [])
                code_nodes = sum(1 for n in nodes if n.get("file_type") == "code")
            except Exception:
                pass
                
        # Query SQLite Alerts
        latest_file = "STABLE"
        try:
            from smart_llm.sqlite_ledger import get_active_alerts
            alerts = get_active_alerts(self.workspace_path, limit=1)
            if alerts:
                filename = alerts[0]["details"].get("file", "UPDATED")
                latest_file = filename.split("/")[-1].upper()
                # Flash LED on new event
                self.canvas.itemconfig(self.led, fill="#39ff14", outline="#ffffff")
                self.root.after(300, lambda: self.canvas.itemconfig(self.led, fill="#39ff14", outline="#39ff14"))
        except Exception:
            pass
            
        # Update text labels
        self.canvas.itemconfig(self.txt_count, text=str(code_nodes))
        self.canvas.itemconfig(self.txt_footer_val, text=latest_file)
        
        # Re-schedule every 2 seconds
        self.root.after(2000, self.update_widget)

    def run(self):
        self.root.mainloop()


def start_widget_app(workspace_path: Path):
    """Start the floating macOS Tkinter widget."""
    app = SmartLLMDesktopWidget(workspace_path)
    app.run()
