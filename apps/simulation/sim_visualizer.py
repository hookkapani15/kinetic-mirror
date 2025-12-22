
"""
Simulation Visualizer
Visualizes the state of the Virtual ESP32 (LEDs and Motors)
"""

import tkinter as tk
from tkinter import ttk
import time
import math
from packages.mirror_core.simulation.mock_serial import get_virtual_device_instance

class SimulationVisualizer:
    def __init__(self, root):
        self.root = root
        # self.root.title("Mirror Body Simulation") # Managed by parent
        # self.root.geometry("800x600") # Managed by parent layout
        
        self.virtual_device = get_virtual_device_instance()
        
        self._create_widgets()
        self._update_loop()

    def _create_widgets(self):
        # Layout: Left side = Motors (64), Right side = LED Matrix
        
        # Main container
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        
        # --- Motor Section (Left) ---
        self.motor_frame = ttk.LabelFrame(main, text="Motors (64)", padding=10)
        # Default pack (will be adjusted by set_mode)
        self.motor_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        self.motor_canvases = []
        
        # Grid layout for 64 motors (8x8)
        motor_grid = ttk.Frame(self.motor_frame)
        motor_grid.pack(fill=tk.BOTH, expand=True)
        
        for i in range(64):
            # Create a small canvas for each motor to show angle
            row = i // 8
            col = i % 8
            
            frame = ttk.Frame(motor_grid)
            frame.grid(row=row, column=col, padx=2, pady=2)
            
            # Simple circular gauge or bar
            c = tk.Canvas(frame, width=40, height=40, bg="#f0f0f0", highlightthickness=0)
            c.pack()
            self.motor_canvases.append(c)
            # Draw initial state
            self._draw_motor(c, 90, i)
            
        # --- LED Panel Section (Right) ---
        self.led_frame = ttk.LabelFrame(main, text="LED Body (16x16 Panels)", padding=10)
        # Default pack
        self.led_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Canvas for LEDs
        # 32x64 pixels. Scale up by 6x -> 192x384
        self.pixel_size = 6
        self.width_leds = 32
        self.height_leds = 64
        self.canvas_w = self.width_leds * self.pixel_size
        self.canvas_h = self.height_leds * self.pixel_size
        
        self.canvas = tk.Canvas(self.led_frame, width=self.canvas_w, height=self.canvas_h, bg="black")
        self.canvas.pack(pady=10, expand=True)

    def set_mode(self, mode):
        """Show/Hide frames based on mode"""
        # Reset visibility
        self.motor_frame.pack_forget()
        self.led_frame.pack_forget()
        
        if mode == "Motor Only":
            self.motor_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        elif mode == "LED Only":
            self.led_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        else: # Both or Unknown
            self.motor_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
            self.led_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    def _draw_motor(self, canvas, angle, index):
        """Draw simple motor visualization"""
        canvas.delete("all")
        w, h = 40, 40
        cx, cy = w/2, h/2
        r = 15
        
        # Draw dial
        canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#999")
        
        # Draw needle
        # 0 deg = left, 180 deg = right
        import math
        rad = math.radians(180 - angle) # Invert because 0 is usually right in math, but servo 0 is left often
        
        nx = cx + r * math.cos(rad)
        ny = cy - r * math.sin(rad)
        
        color = "blue" if angle > 90 else "green"
        canvas.create_line(cx, cy, nx, ny, fill=color, width=2)
        
        # Text
        canvas.create_text(cx, h-5, text=str(index+1), font=("Arial", 7))

    def _update_loop(self):
        state = self.virtual_device.get_server_state()
        
        # Update LEDs
        led_data = state['leds']
        try:
             # Basic rendering
            self.canvas.delete("all")
            # Optimization: Draw all as one batch if possible or just pixels
            # Tkinter canvas is slow for 2048 rects. 
            # Better approach: create image.
            
            # Create a larger image for the canvas
            # We can use PIL or just draw rectangles for now (slow but works for <2000 items)
            # Let's optimize by only drawing lit pixels
            
            for i, brightness in enumerate(led_data):
                if brightness > 5: 
                    x = i % 32 
                    y = i // 32
                    if y >= 64: break 
                    
                    c = int(brightness)
                    color = f"#{c:02x}{c:02x}{c:02x}"
                    
                    x1 = x * self.pixel_size
                    y1 = y * self.pixel_size
                    x2 = x1 + self.pixel_size - 1
                    y2 = y1 + self.pixel_size - 1
                    
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
                    
        except Exception as e:
            pass

        # Update Motors
        angles = state['motors']
        for i, angle in enumerate(angles):
            if i < len(self.motor_canvases):
                self._draw_motor(self.motor_canvases[i], angle, i)

        self.root.after(33, self._update_loop) # ~30fps

if __name__ == "__main__":
    root = tk.Tk()
    app = SimulationVisualizer(root)
    root.mainloop()
