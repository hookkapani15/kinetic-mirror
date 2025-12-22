#!/usr/bin/env python3
"""
Mirror Body Simulation - Main Entry Point
Run this to start the full simulation with LED and Motor control.
"""
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import tkinter as tk
    from led_control_gui import LEDControlApp
    
    root = tk.Tk()
    app = LEDControlApp(root)
    root.mainloop()
