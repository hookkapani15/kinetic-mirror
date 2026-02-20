import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import and run
from apps.gui.main import LEDControlApp
import tkinter as tk

if __name__ == "__main__":
    root = tk.Tk()
    app = LEDControlApp(root)
    root.mainloop()
