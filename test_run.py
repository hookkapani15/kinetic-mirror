import sys
sys.path.insert(0, '.')

import tkinter as tk
from led_control_gui import LEDControlApp

try:
    root = tk.Tk()
    app = LEDControlApp(root)
    root.mainloop()
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    input("Press Enter to exit...")
