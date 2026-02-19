import tkinter as tk
import math
from .theme import COLORS

class BodyGridVisualizer(tk.Canvas):
    """Simple 8x8 grid showing body silhouette - cells light up where body is detected"""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLORS['bg_dark'], highlightthickness=0, **kwargs)
        self.motor_angles = [0] * 64
        self.motor_active = [False] * 64
        self._cell_ids = []
        self._items_created = False
        self.bind('<Configure>', self._on_resize)
    
    def _on_resize(self, event):
        self._items_created = False
        self._draw_grid()
    
    def update_angles(self, angles):
        """Update which cells are active based on motor angles"""
        if len(angles) >= 64:
            for i in range(64):
                self.motor_active[i] = angles[i] > 90
                self.motor_angles[i] = angles[i]
        self._update_cells()
    
    def _draw_grid(self):
        """Draw simple 8x8 colored grid"""
        self.delete('all')
        self._cell_ids = []
        
        w = self.winfo_width()
        h = self.winfo_height()
        
        if w < 20 or h < 20:
            return
        
        margin = 3
        grid_size = min(w, h) - margin * 2
        cell_size = grid_size / 8
        
        start_x = (w - grid_size) / 2
        start_y = (h - grid_size) / 2
        
        for i in range(64):
            row = i // 8
            col = i % 8
            
            x1 = start_x + col * cell_size
            y1 = start_y + row * cell_size
            x2 = x1 + cell_size - 1
            y2 = y1 + cell_size - 1
            
            color = COLORS['success'] if self.motor_active[i] else '#1a1a2e'
            cell_id = self.create_rectangle(x1, y1, x2, y2, 
                                           fill=color, outline='#333344', width=1)
            self._cell_ids.append(cell_id)
        
        self._items_created = True
    
    def _update_cells(self):
        if not self._items_created or len(self._cell_ids) < 64:
            self._draw_grid()
            return
        
        for i in range(64):
            color = COLORS['success'] if self.motor_active[i] else '#1a1a2e'
            self.itemconfig(self._cell_ids[i], fill=color)


class MotorVisualizer(tk.Canvas):
    """Compact 8x8 motor simulation with servo horns"""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLORS['bg_dark'], highlightthickness=0, **kwargs)
        self.motor_angles = [90] * 64
        self.motor_active = [False] * 64
        self._items = {}
        self._items_created = False
        self.bind('<Configure>', self._on_resize)
    
    def _on_resize(self, event):
        self._items_created = False
        self._draw()
    
    def update_angles(self, angles):
        if len(angles) >= 64:
            for i in range(64):
                self.motor_active[i] = angles[i] > 90
                self.motor_angles[i] = angles[i]
        self._update()
    
    def _draw(self):
        self.delete('all')
        self._items = {}
        
        w = self.winfo_width()
        h = self.winfo_height()
        
        if w < 40 or h < 40:
            return
        
        margin = 3
        grid_size = min(w, h) - margin * 2
        cell_size = grid_size / 8
        
        start_x = (w - grid_size) / 2
        start_y = (h - grid_size) / 2
        
        for i in range(64):
            row = i // 8
            col = i % 8
            
            cx = start_x + col * cell_size + cell_size / 2
            cy = start_y + row * cell_size + cell_size / 2
            
            r = cell_size * 0.35
            active = self.motor_active[i]
            angle = self.motor_angles[i]
            
            # Motor body
            body_color = COLORS['motor_active'] if active else '#2a2a3a'
            self._items[f'body_{i}'] = self.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                fill=body_color, outline='#444455', width=1
            )
            
            # Horn
            horn_len = r * 1.2
            rad = math.radians(180 - angle)
            ex = cx + horn_len * math.cos(rad)
            ey = cy - horn_len * math.sin(rad)
            
            horn_color = COLORS['success'] if active else '#555566'
            self._items[f'horn_{i}'] = self.create_line(
                cx, cy, ex, ey, fill=horn_color, width=2
            )
        
        self._items_created = True
    
    def _update(self):
        if not self._items_created:
            self._draw()
            return
        
        w = self.winfo_width()
        h = self.winfo_height()
        
        if w < 40 or h < 40:
            return
        
        margin = 3
        grid_size = min(w, h) - margin * 2
        cell_size = grid_size / 8
        
        start_x = (w - grid_size) / 2
        start_y = (h - grid_size) / 2
        
        for i in range(64):
            row = i // 8
            col = i % 8
            
            cx = start_x + col * cell_size + cell_size / 2
            cy = start_y + row * cell_size + cell_size / 2
            
            r = cell_size * 0.35
            active = self.motor_active[i]
            angle = self.motor_angles[i]
            
            # Update body color
            body_color = COLORS['motor_active'] if active else '#2a2a3a'
            if f'body_{i}' in self._items:
                self.itemconfig(self._items[f'body_{i}'], fill=body_color)
            
            # Update horn
            horn_len = r * 1.2
            rad = math.radians(180 - angle)
            ex = cx + horn_len * math.cos(rad)
            ey = cy - horn_len * math.sin(rad)
            
            horn_color = COLORS['success'] if active else '#555566'
            if f'horn_{i}' in self._items:
                self.coords(self._items[f'horn_{i}'], cx, cy, ex, ey)
                self.itemconfig(self._items[f'horn_{i}'], fill=horn_color)
    
    def draw_motors(self):
        self._draw()
