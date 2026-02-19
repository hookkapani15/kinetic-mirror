"""
Motor Control Simulation - Modern Dark Theme
Controls 64 servo motors based on camera body tracking
ESP32-S3 hardware support with live camera feed and firmware flashing
"""

import tkinter as tk
from tkinter import ttk, messagebox
import time
import math
import threading
import struct
import serial
import serial.tools.list_ports
import numpy as np
import subprocess
import os
import sys
import logging

# ----------------- PATH SETUP -----------------
# Ensure we can import local modules and project packages
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))

if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

# ----------------- IMPORTS -----------------
from core.logging_config import setup_logging
from ui.theme import COLORS
from ui.widgets import ModernButton
from ui.visualizers import BodyGridVisualizer, MotorVisualizer
from ui.camera_panel import CameraPanel
from ui.connection_panel import ConnectionPanel
from ui.manual_panel import ManualControlPanel

# Setup logging
logger = setup_logging()

# Handle MediaPipe check for status indicator
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    logger.warning("MediaPipe not found - tracking status will reflect this")
    MEDIAPIPE_AVAILABLE = False
except Exception as e:
    logger.warning(f"MediaPipe error: {e}")
    MEDIAPIPE_AVAILABLE = False

# Import Mock Serial if available
try:
    from packages.mirror_core.simulation.mock_serial import get_virtual_device_instance
except ImportError:
    get_virtual_device_instance = None
    logger.warning("Mock Serial package not found - simulation may be limited")


class SimulationVisualizer:
    """Main Motor Control Application with Camera Tracking"""
    
    def __init__(self, root):
        self.root = root
        self.root.configure(bg=COLORS['bg_dark'])
        self.virtual_device = None
        self._serial_error_count = 0  # Track serial errors to avoid log spam
        
        if get_virtual_device_instance:
            try:
                self.virtual_device = get_virtual_device_instance()
            except Exception as e:
                logger.warning(f"Virtual device init failed: {e}")
                
        self.serial_port = None
        self.simulation_mode = True
        self.running = True
        self.tracking_enabled = True
        self.control_mode = tk.StringVar(value="Test")  # "Live" or "Test"
        self.smoothing = 0.15
        self.mirror_invert = tk.BooleanVar(value=False)
        self.sync_mode = tk.BooleanVar(value=True) # Default: SYNC ALL
    
        # UI Attributes (declared here for linter)
        self.mode_label = None
        self.status_text = None
        self.camera_panel = None
        self.body_grid = None
        self.motor_viz = None
        self.connection_panel = None
        self.sync_btn = None
        self.smooth_val = tk.DoubleVar(value=0.15)
        self.smooth_lbl = None
        self.control_panel = None
        self.log_text = None
        
        self._create_widgets()
        self._update_tracking_params() # Initial sync to CameraPanel
        self._update_loop()
    
    def _create_widgets(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TCombobox', fieldbackground=COLORS['bg_light'],
                       background=COLORS['bg_light'])
        
        # Main container
        main = tk.Frame(self.root, bg=COLORS['bg_dark'])
        main.pack(fill='both', expand=True, padx=6, pady=6)
        
        # ═══════════════════════════════════════════════════════════════
        # HEADER BAR WITH ALL CONTROLS
        # ═══════════════════════════════════════════════════════════════
        header = tk.Frame(main, bg=COLORS['bg_medium'], height=45)
        header.pack(fill='x', pady=(0, 6))
        header.pack_propagate(False)
        
        # Logo/Title
        tk.Label(header, text="🪞 MIRROR MOTOR CONTROL", 
                bg=COLORS['bg_medium'], fg=COLORS['text_primary'],
                font=('Segoe UI', 13, 'bold')).pack(side='left', padx=10, pady=8)
        
        # Mode selector
        mode_frame = tk.Frame(header, bg=COLORS['bg_medium'])
        mode_frame.pack(side='left', padx=15)
        
        tk.Label(mode_frame, text="Mode:", bg=COLORS['bg_medium'], 
                fg=COLORS['text_secondary'], font=('Segoe UI', 9)).pack(side='left')
        
        mode_combo = ttk.Combobox(mode_frame, textvariable=self.control_mode, 
                                  values=["Live", "Test"], state='readonly', width=6)
        mode_combo.pack(side='left', padx=4)
        mode_combo.bind('<<ComboboxSelected>>', self._on_mode_change)
        
        self.mode_label = tk.Label(mode_frame, text="● LIVE", 
                                   bg=COLORS['bg_medium'], fg=COLORS['success'],
                                   font=('Segoe UI', 10, 'bold'))
        self.mode_label.pack(side='left', padx=8)
        
        # Diagram button
        diagram_btn = ModernButton(header, text="📊 Wiring", 
                                   command=self._show_wiring_diagram,
                                   width=90, height=28,
                                   bg=COLORS['accent_secondary'])
        diagram_btn.pack(side='left', padx=10)
        
        # Status indicators (right side)
        status_frame = tk.Frame(header, bg=COLORS['bg_medium'])
        status_frame.pack(side='right', padx=10)
        
        mp_status = "✓ MediaPipe" if MEDIAPIPE_AVAILABLE else "✗ MediaPipe"
        mp_color = COLORS['success'] if MEDIAPIPE_AVAILABLE else COLORS['error']
        tk.Label(status_frame, text=mp_status, bg=COLORS['bg_medium'], fg=mp_color,
                font=('Segoe UI', 9)).pack(side='right', padx=5)
        
        self.status_text = tk.Label(status_frame, text="Ready", 
                                    bg=COLORS['bg_medium'], fg=COLORS['text_secondary'],
                                    font=('Segoe UI', 9))
        self.status_text.pack(side='right', padx=10)
        
        # ═══════════════════════════════════════════════════════════════
        # MAIN CONTENT: 2/3 Camera + 1/3 Right Panel
        # ═══════════════════════════════════════════════════════════════
        content = tk.Frame(main, bg=COLORS['bg_dark'])
        content.pack(fill='both', expand=True)
        
        # Use grid for 2/3 + 1/3 split
        content.grid_columnconfigure(0, weight=2)  # Camera gets 2 parts
        content.grid_columnconfigure(1, weight=1)  # Right panel gets 1 part
        content.grid_rowconfigure(0, weight=1)
        
        # LEFT: Camera Panel (2/3 width)
        self.camera_panel = CameraPanel(content, 
                                       on_angle_change=self._on_angle_change)
        self.camera_panel.grid(row=0, column=0, sticky='nsew', padx=(0, 4))
        
        # RIGHT: Visualizers + Controls (1/3 width)
        right_panel = tk.Frame(content, bg=COLORS['bg_medium'])
        right_panel.grid(row=0, column=1, sticky='nsew', padx=(4, 0))
        
        # ─────────────────────────────────────────────────────────────
        # 1. SYSTEM LOG (Anchored Bottom - Fixed Height)
        # ─────────────────────────────────────────────────────────────
        log_frame = tk.Frame(right_panel, bg=COLORS['bg_medium'], height=110)
        log_frame.pack(side='bottom', fill='x', padx=4, pady=(2, 6))
        log_frame.pack_propagate(False)
        
        log_h = tk.Frame(log_frame, bg=COLORS['bg_medium'])
        log_h.pack(fill='x')
        tk.Label(log_h, text="📋 SYSTEM LOG", bg=COLORS['bg_medium'], 
                fg=COLORS['text_primary'], font=('Segoe UI', 8, 'bold')).pack(side='left')
        tk.Button(log_h, text="Clear", command=self._clear_log, bg=COLORS['bg_light'],
                 fg=COLORS['text_secondary'], font=('Segoe UI', 7), bd=0, padx=4).pack(side='right')
        
        log_bg = tk.Frame(log_frame, bg='#0a0a15', padx=1, pady=1)
        log_bg.pack(fill='both', expand=True, pady=2)
        
        self.log_text = tk.Text(log_bg, bg='#0a0a15', fg='#00ff00', font=('Consolas', 9),
                               state='disabled', wrap='word', bd=0)
        self.log_text.pack(side='left', fill='both', expand=True)
        
        log_sc = ttk.Scrollbar(log_bg, orient='vertical', command=self.log_text.yview)
        log_sc.pack(side='right', fill='y')
        self.log_text['yscrollcommand'] = log_sc.set

        # ─────────────────────────────────────────────────────────────
        # 2. DASHBOARD (Visualizers - Top)
        # ─────────────────────────────────────────────────────────────
        viz_frame = tk.Frame(right_panel, bg=COLORS['bg_medium'])
        viz_frame.pack(side='top', fill='x', padx=4, pady=4)
        
        viz_t = tk.Frame(viz_frame, bg=COLORS['bg_medium'])
        viz_t.pack(fill='x')
        tk.Label(viz_t, text="📊 DETECTION", bg=COLORS['bg_medium'], fg=COLORS['text_primary'], font=('Segoe UI', 8, 'bold')).pack(side='left', expand=True)
        tk.Label(viz_t, text="⚙️ SIMULATION", bg=COLORS['bg_medium'], fg=COLORS['text_primary'], font=('Segoe UI', 8, 'bold')).pack(side='right', expand=True)
        
        viz_c = tk.Frame(viz_frame, bg=COLORS['bg_dark'])
        viz_c.pack(fill='x', pady=2)
        viz_c.grid_columnconfigure((0,1), weight=1)
        
        self.body_grid = BodyGridVisualizer(viz_c, height=100)
        self.body_grid.grid(row=0, column=0, sticky='nsew', padx=(0, 2))
        self.motor_viz = MotorVisualizer(viz_c, height=100)
        self.motor_viz.grid(row=0, column=1, sticky='nsew', padx=(2, 0))

        # ─────────────────────────────────────────────────────────────
        # 3. CONTROL GRID (4 COMPACT BOXES)
        # ─────────────────────────────────────────────────────────────
        grid_frame = tk.Frame(right_panel, bg=COLORS['bg_medium'])
        grid_frame.pack(side='top', fill='both', expand=True, padx=4, pady=2)
        
        # Grid setup: 2 columns
        grid_frame.grid_columnconfigure((0, 1), weight=1)
        grid_frame.grid_rowconfigure((0, 1), weight=1)

        # BOX 1: HARDWARE (Compact)
        box1 = tk.LabelFrame(grid_frame, text=" 🔌 HARDWARE ", bg=COLORS['bg_medium'], fg=COLORS['text_primary'], font=('Segoe UI', 8, 'bold'), padx=4, pady=4)
        box1.grid(row=0, column=0, sticky='nsew', padx=2, pady=2)
        self.connection_panel = ConnectionPanel(box1, on_connect=self._on_connect, on_disconnect=self._on_disconnect, main_log=self._log)
        self.connection_panel.pack(fill='both', expand=True)

        # BOX 2: MOTION MODE (The Switch)
        box2 = tk.LabelFrame(grid_frame, text=" ⚙️ TRACKING ", bg=COLORS['bg_medium'], fg=COLORS['text_primary'], font=('Segoe UI', 8, 'bold'), padx=4, pady=4)
        box2.grid(row=0, column=1, sticky='nsew', padx=2, pady=2)
        
        # Mode Toggle Button (High Visibility Switch)
        self.sync_btn = tk.Button(box2, text="MODE: SYNC (ALL)", 
                                 command=self._toggle_sync_mode,
                                 bg='#1a2a1a', fg=COLORS['success'],
                                 activebackground=COLORS['accent'],
                                 activeforeground='white',
                                 bd=1, relief='solid', font=('Segoe UI', 10, 'bold'), height=2)
        self.sync_btn.pack(fill='x', pady=(2, 8))
        
        opts_f = tk.Frame(box2, bg=COLORS['bg_medium'])
        opts_f.pack(fill='x')
        tk.Checkbutton(opts_f, text="Invert Axis", variable=self.mirror_invert, 
                       command=self._update_tracking_params,
                       bg=COLORS['bg_medium'], fg=COLORS['text_primary'],
                       selectcolor=COLORS['bg_dark'], font=('Segoe UI', 8)).pack(side='left')
        
        tk.Button(opts_f, text="Reset", command=self._reset_motors, 
                 bg=COLORS['warning'], fg='black', bd=0, padx=8, font=('Segoe UI', 8, 'bold')).pack(side='right')

        # BOX 3: TOOLS & FX
        box3 = tk.LabelFrame(grid_frame, text=" ✨ EFFECTS ", bg=COLORS['bg_medium'], fg=COLORS['text_primary'], font=('Segoe UI', 8, 'bold'), padx=4, pady=4)
        box3.grid(row=1, column=0, sticky='nsew', padx=2, pady=2)
        
        sm_v = tk.Frame(box3, bg=COLORS['bg_medium'])
        sm_v.pack(fill='x', pady=(0, 2))
        self.smooth_val = tk.DoubleVar(value=0.15)
        ttk.Scale(sm_v, from_=0.01, to=0.5, variable=self.smooth_val, command=self._update_smoothing).pack(side='left', fill='x', expand=True)
        self.smooth_lbl = tk.Label(sm_v, text="15%", bg=COLORS['bg_medium'], fg=COLORS['text_secondary'], font=('Segoe UI', 7), width=3)
        self.smooth_lbl.pack(side='right')

        fx_grid = tk.Frame(box3, bg=COLORS['bg_medium'])
        fx_grid.pack(fill='both', expand=True)
        fx_grid.grid_columnconfigure((0,1), weight=1)
        for i, (txt, cmd) in enumerate([("Wave", 'wave'), ("Breathe", 'breathe'), ("Ripple", 'ripple'), ("Random", 'random')]):
            tk.Button(fx_grid, text=txt, command=lambda c=cmd: self._run_effect(c), 
                     bg=COLORS['bg_dark'], fg='white', bd=0, font=('Segoe UI', 7), pady=2).grid(row=i//2, column=i%2, sticky='ew', padx=1, pady=1)

        # BOX 4: MANUAL CONTROL
        box4 = tk.LabelFrame(grid_frame, text=" 🎮 MANUAL ", bg=COLORS['bg_medium'], fg=COLORS['text_primary'], font=('Segoe UI', 8, 'bold'), padx=4, pady=4)
        box4.grid(row=1, column=1, sticky='nsew', padx=2, pady=2)
        self.control_panel = ManualControlPanel(box4, on_angle_change=self._on_angle_change, main_log=self._log)
        self.control_panel.pack(fill='both', expand=True)

        # LINK DETECTION VIZ (Now that both exist)
        self.camera_panel.on_detection_change = self.body_grid.update_angles

        self._log("UI layout updated - Compact Grid Mode")
        self._log("System ready in Stacked Card Mode")
    
    def _log(self, message):
        """Add a message to the live log"""
        try:
            timestamp = time.strftime("%H:%M:%S")
            self.log_text.config(state='normal')
            self.log_text.insert('end', f"[{timestamp}] {message}\n")
            self.log_text.see('end')
            self.log_text.config(state='disabled')
            # Also log to file via logger
            logger.info(message) 
        except:
            pass
    
    def _clear_log(self):
        """Clear the log"""
        try:
            self.log_text.config(state='normal')
            self.log_text.delete('1.0', 'end')
            self.log_text.config(state='disabled')
        except:
            pass
    
    def _on_mode_change(self, event=None):
        mode = self.control_mode.get()
        if mode == "Live":
            self.mode_label.config(text="● LIVE", fg=COLORS['success'])
            self.status_text.config(text="Live tracking")
        else:
            self.mode_label.config(text="● TEST", fg=COLORS['accent_secondary'])
            self.status_text.config(text="Manual control")
    
    def _on_body_position(self, x_position):
        """Handle body position change from camera tracking"""
        if not self.tracking_enabled:
            return
        if self.control_mode.get() != "Live":
            return
            
        # Apply Mirror Invert if enabled
        if hasattr(self, 'mirror_invert') and self.mirror_invert.get():
            x_position = 1.0 - x_position
            
        # Map body X position (0-1) to motor angles
        angles = []
        center_motor = int(x_position * 8)
        for i in range(64):
            row = i // 8
            col = i % 8
            dist = abs(col - center_motor)
            strength = max(0.0, 1.0 - (dist / 4.0))
            angle = 90 + (x_position - 0.5) * 180 * strength
            angle = int(max(0.0, min(180.0, float(angle))))
            angles.append(angle)
        self._on_angle_change(angles)
    
    def _on_connect(self, serial_port, is_simulation):
        self.serial_port = serial_port
        self.simulation_mode = is_simulation
        
        if is_simulation:
            self.mode_label.config(text="[ SIMULATION ]", fg=COLORS['warning'])
            self.status_text.config(text="Simulation mode - motors visualized only")
        else:
            self.mode_label.config(text="[ HARDWARE ]", fg=COLORS['success'])
            self.status_text.config(text="Connected to ESP32 - motors active!")
            self._log("Connected to hardware!")
            
            # Auto-switch to Live mode
            self.control_mode.set("Live")
            self._on_mode_change()
            self._log("Switched to Live mode")
    
    def _show_wiring_diagram(self):
        """Show wiring diagram in a new window"""
        diagram_window = tk.Toplevel(self.root)
        diagram_window.title("Wiring Diagram - ESP32 + PCA9685")
        diagram_window.geometry("800x600")
        diagram_window.configure(bg=COLORS['bg_dark'])
        
        # Center the window
        diagram_window.update_idletasks()
        x = (diagram_window.winfo_screenwidth() - 800) // 2
        y = (diagram_window.winfo_screenheight() - 600) // 2
        diagram_window.geometry(f"+{x}+{y}")
        
        # Title
        title = tk.Label(diagram_window, text="🔌 ESP32 + PCA9685 Wiring Diagram",
                        bg=COLORS['bg_dark'], fg=COLORS['text_primary'],
                        font=('Segoe UI', 16, 'bold'))
        title.pack(pady=10)
        
        # Canvas for diagram
        canvas = tk.Canvas(diagram_window, width=760, height=450, 
                          bg=COLORS['bg_medium'], highlightthickness=0)
        canvas.pack(pady=10)
        
        # Draw ESP32
        esp_x, esp_y = 150, 100
        esp_w, esp_h = 120, 200
        canvas.create_rectangle(esp_x, esp_y, esp_x+esp_w, esp_y+esp_h, 
                               fill='#2D4A3E', outline='#4CAF50', width=2)
        canvas.create_text(esp_x+esp_w//2, esp_y+20, text="ESP32", 
                          fill='white', font=('Segoe UI', 12, 'bold'))
        
        # ESP32 Pins
        esp_pins = [
            ("3.3V", 40), ("GND", 60), ("D18 (SDA)", 100), ("D19 (SCL)", 120),
            ("D5 (LED1)", 160), ("VIN (5V)", 80)
        ]
        for pin_name, y_off in esp_pins:
            canvas.create_text(esp_x+esp_w+10, esp_y+y_off, text=pin_name,
                              fill='#4CAF50', font=('Consolas', 9), anchor='w')
            canvas.create_oval(esp_x+esp_w-5, esp_y+y_off-3, esp_x+esp_w+5, esp_y+y_off+3,
                              fill='#4CAF50', outline='')
        
        # Draw PCA9685 boards (smaller, 4 in 2x2 grid)
        pca_w, pca_h = 120, 70
        
        # PCA9685 #1 (0x40)
        pca1_x, pca1_y = 400, 60
        canvas.create_rectangle(pca1_x, pca1_y, pca1_x+pca_w, pca1_y+pca_h,
                               fill='#4A2D4A', outline='#9C27B0', width=2)
        canvas.create_text(pca1_x+pca_w//2, pca1_y+15, text="PCA9685 #1",
                          fill='white', font=('Segoe UI', 9, 'bold'))
        canvas.create_text(pca1_x+pca_w//2, pca1_y+35, text="0x40 | Servos 0-15",
                          fill='#CE93D8', font=('Consolas', 8))
        
        # PCA9685 #2 (0x41)
        pca2_x, pca2_y = 550, 60
        canvas.create_rectangle(pca2_x, pca2_y, pca2_x+pca_w, pca2_y+pca_h,
                               fill='#4A2D3E', outline='#E91E63', width=2)
        canvas.create_text(pca2_x+pca_w//2, pca2_y+15, text="PCA9685 #2",
                          fill='white', font=('Segoe UI', 9, 'bold'))
        canvas.create_text(pca2_x+pca_w//2, pca2_y+35, text="0x41 | Servos 16-31",
                          fill='#F48FB1', font=('Consolas', 8))
        
        # PCA9685 #3 (0x42)
        pca3_x, pca3_y = 400, 150
        canvas.create_rectangle(pca3_x, pca3_y, pca3_x+pca_w, pca3_y+pca_h,
                               fill='#2D4A4A', outline='#00BCD4', width=2)
        canvas.create_text(pca3_x+pca_w//2, pca3_y+15, text="PCA9685 #3",
                          fill='white', font=('Segoe UI', 9, 'bold'))
        canvas.create_text(pca3_x+pca_w//2, pca3_y+35, text="0x42 | Servos 32-47",
                          fill='#80DEEA', font=('Consolas', 8))
        
        # PCA9685 #4 (0x43)
        pca4_x, pca4_y = 550, 150
        canvas.create_rectangle(pca4_x, pca4_y, pca4_x+pca_w, pca4_y+pca_h,
                               fill='#4A4A2D', outline='#CDDC39', width=2)
        canvas.create_text(pca4_x+pca_w//2, pca4_y+15, text="PCA9685 #4",
                          fill='white', font=('Segoe UI', 9, 'bold'))
        canvas.create_text(pca4_x+pca_w//2, pca4_y+35, text="0x43 | Servos 48-63",
                          fill='#E6EE9C', font=('Consolas', 8))
        
        # Draw wires
        # I2C Bus line (SDA + SCL combined for simplicity)
        canvas.create_line(esp_x+esp_w+5, esp_y+100, 330, esp_y+100,
                          fill='#2196F3', width=3)
        canvas.create_text(330, esp_y+100-10, text="SDA (D18)", fill='#2196F3',
                          font=('Consolas', 8))
        
        canvas.create_line(esp_x+esp_w+5, esp_y+120, 330, esp_y+120,
                          fill='#FF9800', width=3)
        canvas.create_text(330, esp_y+120-10, text="SCL (D19)", fill='#FF9800',
                          font=('Consolas', 8))
        
        # I2C bus to all PCA boards
        canvas.create_line(330, esp_y+100, 330, pca3_y+pca_h+10,
                          fill='#2196F3', width=2)
        canvas.create_line(350, esp_y+120, 350, pca3_y+pca_h+10,
                          fill='#FF9800', width=2)
        
        # Connect to each PCA
        for pca_x, pca_y_pos in [(pca1_x, pca1_y+pca_h//2), (pca2_x, pca2_y+pca_h//2),
                                 (pca3_x, pca3_y+pca_h//2), (pca4_x, pca4_y+pca_h//2)]:
            canvas.create_line(330, pca_y_pos, pca_x, pca_y_pos,
                              fill='#2196F3', width=1, dash=(2, 2))
        
        # VCC/GND indicators
        canvas.create_text(pca1_x+pca_w//2, pca1_y+pca_h-10, text="VCC|GND|V+",
                          fill='#9E9E9E', font=('Consolas', 7))
        
        # I2C chain indicator
        canvas.create_text(475, 130, text="I2C Bus (all share SDA/SCL)",
                          fill='#9E9E9E', font=('Consolas', 8))
        
        # Legend
        legend_y = 390
        canvas.create_text(50, legend_y, text="WIRING LEGEND:", 
                          fill='white', font=('Segoe UI', 10, 'bold'), anchor='w')
        
        legend_items = [
            ("SDA (GPIO 18)", '#2196F3', 50),
            ("SCL (GPIO 19)", '#FF9800', 200),
            ("VCC (3.3V)", '#F44336', 350),
            ("GND", '#424242', 470),
        ]
        for text, color, x_pos in legend_items:
            canvas.create_rectangle(x_pos, legend_y+20, x_pos+20, legend_y+30, fill=color)
            canvas.create_text(x_pos+25, legend_y+25, text=text, fill='white',
                              font=('Consolas', 9), anchor='w')
        
        # Instructions
        instructions = tk.Text(diagram_window, height=4, width=90, bg=COLORS['bg_light'],
                              fg=COLORS['text_secondary'], font=('Consolas', 9),
                              state='normal', wrap='word')
        instructions.pack(pady=10, padx=20)
        instructions.insert('1.0', """CONNECTIONS:
ESP32 D18 (SDA) → PCA9685 SDA pins (both boards)
ESP32 D19 (SCL) → PCA9685 SCL pins (both boards)
ESP32 GND → PCA9685 GND (both boards)
ESP32 VIN (5V) → Servo power supply (external recommended for 32 servos)
PCA9685 VCC → 3.3V (logic) | V+ → 5V (servo power)""")
        instructions.config(state='disabled')
        
        # Close button
        close_btn = ModernButton(diagram_window, text="Close", 
                                command=diagram_window.destroy,
                                width=100, height=32, bg=COLORS['error'])
        close_btn.pack(pady=10)
    
    def _on_disconnect(self):
        self.serial_port = None
        self.simulation_mode = True
        self.mode_label.config(text="[ DISCONNECTED ]", fg=COLORS['error'])
        self.status_text.config(text="Disconnected")
        
        # Auto-switch to Test mode
        self.control_mode.set("Test")
        self._on_mode_change()
        self._log("Switched to Test mode")
        
    def _reset_motors(self):
        """Reset all motors to 0 degrees"""
        self._log("Resetting all motors to 0°")
        angles = np.full(64, 0)
        self._on_angle_change(angles)
    
    def _run_effect(self, effect_name):
        """Run a preset motion effect (5 seconds)"""
        self._log(f"Starting effect: {effect_name.capitalize()}")
        if self.control_mode.get() != "Test":
            self.control_mode.set("Test")
            self._on_mode_change()
            
        def run():
            t = 0
            start_time = time.time()
            import random # Ensure import
            
            while self.control_mode.get() == "Test":
                angles = []
                for i in range(64):
                    row = i // 8
                    col = i % 8
                    val = 90
                    
                    if effect_name == 'wave':
                         val = 90 + 45 * math.sin(t*0.2 + col*0.5)
                    elif effect_name == 'breathe':
                         val = 90 + 45 * math.sin(t*0.1)
                    elif effect_name == 'ripple':
                         dist = math.sqrt((row-3.5)**2 + (col-3.5)**2)
                         val = 90 + 50 * math.sin(t*0.2 - dist*0.5)
                    elif effect_name == 'random':
                         val = random.randint(45, 135)
                    
                    val = int(max(0.0, min(180.0, float(val))))
                    angles.append(val)
                
                self._on_angle_change(np.array(angles, dtype=np.uint8))
                time.sleep(0.05)
                t += 1
                
                # Run for 5 seconds
                if time.time() - start_time > 5:
                    break
            
            self._log(f"Effect {effect_name} complete")
            # Nice finish: reset to 90
            self._on_angle_change(np.full(64, 90))
                
        threading.Thread(target=run, daemon=True).start()

    def _update_smoothing(self, val):
        try:
            val = float(val)
            self.smoothing = val
            self.smooth_lbl.config(text=f"{int(val*100)}%")
            self._update_tracking_params()
        except:
            pass

    def _toggle_sync_mode(self):
        """Toggle between Silhouette and Synchronized modes"""
        if self.sync_mode.get():
            self.sync_mode.set(False)
            self.sync_btn.config(text="MODE: SILHOUETTE", fg=COLORS['accent'], bg='#2a1a1a')
            self._log("Mode: Individual Silhouette Tracking")
        else:
            self.sync_mode.set(True)
            self.sync_btn.config(text="MODE: SYNC (ALL)", fg=COLORS['success'], bg='#1a2a1a')
            self._log("Mode: Joined Synchronized Movement")
        self._update_tracking_params()

    def _update_tracking_params(self):
        """Update CameraPanel with latest tracking settings"""
        if hasattr(self, 'camera_panel'):
            # Pass smoothing (inverted scale: 0.15 responsiveness -> 0.85 smoothing factor)
            s_factor = 1.0 - self.smoothing
            self.camera_panel.set_tracking_params(
                sync_mode=self.sync_mode.get(),
                invert=self.mirror_invert.get(),
                smoothing=s_factor
            )
    
    def _on_angle_change(self, angles):
        """Handle angle changes from any source"""
        # Update motor visualizer ONLY
        self.motor_viz.update_angles(angles)
        
        # Always try to send if we have a serial port (hardware mode)
        if self.serial_port:
            self._send_motor_packet(angles)
        
        if self.simulation_mode and self.virtual_device:
            try:
                self.virtual_device._motors = list(angles)
            except:
                pass
    
    def _send_motor_packet(self, angles):
        """Send motor angles to ESP32 (optimized with struct.pack)"""
        if not self.serial_port:
            return
        
        # Guard: check port is still open
        try:
            if not self.serial_port.is_open:
                self._serial_error_count += 1
                if self._serial_error_count == 1:
                    logger.warning("Serial port closed unexpectedly")
                return
        except Exception:
            return
        
        try:
            # Ensure we have 64 angles (pad with 90 if needed)
            motor_angles = list(angles[:64]) + [90] * max(0, 64 - len(angles))
            
            # Build packet efficiently with struct
            # Header: 0xAA 0xBB 0x02
            values = []
            for angle in motor_angles:
                a = max(0, min(180, int(angle)))
                values.append(int((a / 180.0) * 1000))
            
            packet = b'\xAA\xBB\x02' + struct.pack('>' + 'H' * 64, *values)
            self.serial_port.write(packet)
            self._serial_error_count = 0  # Reset on success
            
        except serial.SerialTimeoutException:
            # Buffer full - clear it and skip this packet
            try:
                self.serial_port.reset_output_buffer()
            except Exception:
                pass
        except (OSError, serial.SerialException) as e:
            self._serial_error_count += 1
            if self._serial_error_count <= 3:
                logger.warning(f"Serial error ({self._serial_error_count}): {e}")
            if self._serial_error_count >= 10:
                logger.error("Too many serial errors — auto-disconnecting")
                self.serial_port = None
                self.root.after(0, lambda: self.connection_panel._disconnect())
        except Exception as e:
            self._serial_error_count += 1
            if self._serial_error_count <= 3:
                logger.error(f"Send error: {e}")
    
    def _update_loop(self):
        """Main update loop for simulation sync"""
        if not self.running:
            return
        
        # Sync from virtual device if needed
        if self.simulation_mode and self.virtual_device:
            try:
                state = self.virtual_device.get_server_state()
                # Only update if not being controlled by camera
                if not self.camera_panel.running:
                    motor_angles = state.get('motors', [90] * 64)
                    self.motor_viz.update_angles(motor_angles)
            except Exception:
                pass  # Virtual device may not be available
        
        self.root.after(50, self._update_loop)
    
    def stop(self):
        """Stop the application cleanly"""
        self.running = False
        
        # Stop camera panel
        try:
            self.camera_panel.stop()
        except Exception:
            pass
        
        # Stop connection monitor thread
        try:
            self.connection_panel.monitor_running = False
        except Exception:
            pass
        
        # Close serial port
        if self.serial_port:
            try:
                self.serial_port.reset_output_buffer()
            except Exception:
                pass
            try:
                self.serial_port.close()
            except Exception:
                pass


def kill_duplicate_processes():
    """Kill any other instances of this script running"""
    try:
        import psutil
    except ImportError:
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'psutil', '-q'], capture_output=True)
            import psutil
        except Exception:
            logger.warning("psutil not available — skipping duplicate check")
            return 0
    
    current_pid = os.getpid()
    # Match both old and new script names
    script_names = ['sim_visualizer', 'apps.gui.main', 'apps/gui/main', 'apps\\gui\\main']
    killed_count = 0
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['pid'] == current_pid:
                continue
            
            cmdline = proc.info.get('cmdline') or []
            cmdline_str = ' '.join(cmdline).lower()
            
            # Check if this is another instance of our script
            if 'python' in proc.info.get('name', '').lower():
                if any(name in cmdline_str for name in script_names):
                    logger.info(f"Killing duplicate process: PID {proc.info['pid']}")
                    proc.kill()
                    killed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    return killed_count


if __name__ == "__main__":
    # AUTO-KILL: Terminate any other running instances first
    killed = kill_duplicate_processes()
    if killed > 0:
        logger.info(f"[AUTO-KILL] Terminated {killed} duplicate instance(s)")
        time.sleep(0.5)  # Allow resources to be released
    
    root = tk.Tk()
    root.title("Motor Control System")
    root.geometry("1200x700")
    root.configure(bg=COLORS['bg_dark'])
    
    root.update_idletasks()
    x = (root.winfo_screenwidth() - 1200) // 2
    y = (root.winfo_screenheight() - 700) // 2
    root.geometry(f"+{x}+{y}")
    
    try:
        app = SimulationVisualizer(root)
        
        def on_close():
            app.stop()
            root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_close)
        root.mainloop()
    except Exception as e:
        import traceback
        # We might not have logger configured yet if it crashed early, but try
        try:
            logger.critical(f"FATAL ERROR: GUI crashed during startup: {e}")
            logger.critical(traceback.format_exc())
        except:
            print(f"\n[FATAL ERROR] GUI crashed during startup: {e}")
            traceback.print_exc()
        sys.exit(1)
