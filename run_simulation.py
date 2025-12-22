
"""
Run Simulation
Starts the LED Control GUI, which now includes the simulation visualizer.
"""

import os
import sys
import subprocess

if __name__ == "__main__":
    print("Starting LED Control GUI (which includes Simulation support)...")
    
    # Ensure package root is in pythonpath
    env = os.environ.copy()
    env['PYTHONPATH'] = os.getcwd()
    
    # Run the main GUI
    subprocess.run([sys.executable, "led_control_gui.py"], env=env)
