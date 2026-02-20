import tkinter as tk
from .theme import COLORS

class ModernButton(tk.Canvas):
    """Modern rounded button with hover effects"""
    def __init__(self, parent, text, command=None, width=120, height=36, 
                 bg=None, fg=None, **kwargs):
        if bg is None:
            bg = COLORS['accent']
        if fg is None:
            fg = COLORS['text_primary']
        super().__init__(parent, width=width, height=height, 
                        bg=COLORS['bg_dark'], highlightthickness=0, **kwargs)
        self.command = command
        self.text = text
        self.default_bg = bg
        self.current_bg = bg
        self.fg = fg
        self.width = width
        self.height = height
        self.enabled = True
        
        self._draw()
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<Button-1>', self._on_click)
    
    def _draw(self):
        self.delete('all')
        r = 8
        x1, y1 = 2, 2
        x2, y2 = self.width - 2, self.height - 2
        
        self.create_arc(x1, y1, x1 + 2*r, y1 + 2*r, start=90, extent=90, 
                       fill=self.current_bg, outline='')
        self.create_arc(x2 - 2*r, y1, x2, y1 + 2*r, start=0, extent=90, 
                       fill=self.current_bg, outline='')
        self.create_arc(x1, y2 - 2*r, x1 + 2*r, y2, start=180, extent=90, 
                       fill=self.current_bg, outline='')
        self.create_arc(x2 - 2*r, y2 - 2*r, x2, y2, start=270, extent=90, 
                       fill=self.current_bg, outline='')
        self.create_rectangle(x1 + r, y1, x2 - r, y2, fill=self.current_bg, outline='')
        self.create_rectangle(x1, y1 + r, x2, y2 - r, fill=self.current_bg, outline='')
        
        self.create_text(self.width/2, self.height/2, text=self.text, 
                        fill=self.fg, font=('Segoe UI', 10, 'bold'))
    
    def _on_enter(self, e):
        if self.enabled:
            self.current_bg = self._lighten_color(self.default_bg, 0.2)
            self._draw()
    
    def _on_leave(self, e):
        self.current_bg = self.default_bg
        self._draw()
    
    def _on_click(self, e):
        if self.enabled and self.command:
            self.command()
    
    def _lighten_color(self, hex_color, factor):
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:], 16)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def set_enabled(self, enabled):
        self.enabled = enabled
        if not enabled:
            self.current_bg = COLORS['motor_neutral']
        else:
            self.current_bg = self.default_bg
        self._draw()
    
    def set_text(self, text):
        self.text = text
        self._draw()

    def set_color(self, color):
        self.default_bg = color
        self.current_bg = color
        self._draw()
