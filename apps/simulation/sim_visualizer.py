
"""
Simulation Visualizer
Visualizes the state of the Virtual ESP32 (LEDs only - LED branch)
"""

import tkinter as tk
from tkinter import ttk
import time
import math
from shared.io.mock_serial import get_virtual_device_instance

class SimulationVisualizer:
    def __init__(self, root):
        self.root = root
        
        self.virtual_device = get_virtual_device_instance()
        
        self._create_widgets()
        self._update_loop()

    def _create_widgets(self):
        # Main container
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        
        # --- LED Panel Section ---
        self.led_frame = ttk.LabelFrame(main, text="LED Body (32x64)", padding=10)
        self.led_frame.pack(fill=tk.BOTH, expand=True)
        
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
        """Mode setter (kept for compatibility, but LED branch only supports LED Only)"""
        pass  # No mode switching needed on LED branch

    def _update_loop(self):
        state = self.virtual_device.get_server_state()
        
        # Update LEDs
        led_data = state['leds']
        try:
            self.canvas.delete("all")
            
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

        self.root.after(33, self._update_loop) # ~30fps

if __name__ == "__main__":
    root = tk.Tk()
    app = SimulationVisualizer(root)
    root.mainloop()
