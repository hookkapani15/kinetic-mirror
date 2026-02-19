import tkinter as tk
import math
import threading
import time
from .theme import COLORS
from .widgets import ModernButton

class ManualControlPanel(tk.Frame):
    """Compact manual control panel"""
    def __init__(self, parent, on_angle_change=None, main_log=None, **kwargs):
        super().__init__(parent, bg=COLORS['bg_medium'], **kwargs)
        
        self.on_angle_change = on_angle_change
        self.main_log = main_log
        self.current_angles = [90] * 64
        self.testing = False
        
        # UI Attributes (declared here for linter)
        self.angle_display = None
        self.slider = None
        self.wave_btn = None
        self.test_btn = None
        
        self._create_widgets()
    
    def _create_widgets(self):
        title = tk.Label(self, text="🎛️ MANUAL", 
                        bg=COLORS['bg_medium'], fg=COLORS['text_primary'],
                        font=('Segoe UI', 10, 'bold'))
        title.pack(pady=(8, 5))
        
        # Angle display
        self.angle_display = tk.Label(self, text="90°", 
                                      bg=COLORS['bg_medium'], fg=COLORS['accent_secondary'],
                                      font=('Segoe UI', 18, 'bold'))
        self.angle_display.pack(pady=5)
        
        # Slider
        self.slider = tk.Scale(self, from_=0, to=180, orient='horizontal',
                               bg=COLORS['bg_light'], fg=COLORS['text_primary'],
                               troughcolor=COLORS['bg_dark'], 
                               highlightthickness=0, length=150,
                               command=self._on_slider)
        self.slider.set(90)
        self.slider.pack(padx=10, pady=5)
        
        # Presets
        presets_frame = tk.Frame(self, bg=COLORS['bg_medium'])
        presets_frame.pack(fill='x', padx=10, pady=5)
        
        for text, angle in [("0°", 0), ("90°", 90), ("180°", 180)]:
            btn = tk.Button(presets_frame, text=text, 
                           command=lambda a=angle: self._set_angle(a),
                           bg=COLORS['bg_light'], fg=COLORS['text_primary'],
                           font=('Segoe UI', 8), bd=0, padx=8, pady=3)
            btn.pack(side='left', padx=2, expand=True, fill='x')
        
        # Wave button
        self.wave_btn = ModernButton(self, text="🌊 Wave", 
                                     command=self._start_wave,
                                     width=80, height=26,
                                     bg=COLORS['accent_secondary'])
        self.wave_btn.pack(pady=5)
        
        # Test Motors button
        self.test_btn = ModernButton(self, text="🔧 Test", 
                                    command=self._test_motors,
                                    width=80, height=26,
                                    bg=COLORS['success'])
        self.test_btn.pack(pady=3)

        # ---------------- Verification Suite ----------------
        tk.Label(self, text="🛡️ VERIFICATION", 
                 bg=COLORS['bg_medium'], fg=COLORS['text_secondary'],
                 font=('Segoe UI', 8, 'bold')).pack(pady=(10, 2))
        
        v_frame = tk.Frame(self, bg=COLORS['bg_medium'])
        v_frame.pack(fill='x', padx=5)
        
        tk.Button(v_frame, text="Ping Test", command=self._verify_ping,
                 bg=COLORS['bg_light'], fg='white', bd=0, font=('Segoe UI', 7), pady=3).pack(side='left', expand=True, fill='x', padx=1)
        tk.Button(v_frame, text="Scan Rows", command=self._verify_scan,
                 bg=COLORS['bg_light'], fg='white', bd=0, font=('Segoe UI', 7), pady=3).pack(side='left', expand=True, fill='x', padx=1)

    def _log(self, msg):
        if self.main_log:
            self.main_log(f"[VERIFY] {msg}")
        else:
            print(f"[VERIFY] {msg}")

    def _verify_ping(self):
        """Quick ping test: Move Motor 0 to verify real-time link"""
        def run():
            self._log("Starting Ping Test...")
            self._log("Sending: Motor 0 -> 180°")
            angles = [90] * 64
            angles[0] = 180
            if self.on_angle_change: self.on_angle_change(angles)
            time.sleep(0.8)
            
            self._log("Sending: Motor 0 -> 0°")
            angles[0] = 0
            if self.on_angle_change: self.on_angle_change(angles)
            time.sleep(0.8)
            
            self._log("Sending: Motor 0 -> 90° (Center)")
            angles[0] = 90
            if self.on_angle_change: self.on_angle_change(angles)
            self._log("Ping Test Complete.")
            
        threading.Thread(target=run, daemon=True).start()

    def _verify_scan(self):
        """Scan through rows to verify driver configuration"""
        def run():
            self._log("Starting Row Scan...")
            for row in range(8):
                self._log(f"Scanning Row {row} (Motors {row*8}-{row*8+7})")
                angles = [90] * 64
                for col in range(8):
                    angles[row*8 + col] = 135
                if self.on_angle_change: self.on_angle_change(angles)
                time.sleep(0.5)
                
                angles = [90] * 64
                if self.on_angle_change: self.on_angle_change(angles)
                time.sleep(0.2)
            
            self._log("Row Scan Complete.")
            
        threading.Thread(target=run, daemon=True).start()
    
    def _on_slider(self, value):
        angle = int(float(value))
        self.angle_display.config(text=f"{angle}°")
        self._set_angle(angle)
    
    def _set_angle(self, angle):
        self.current_angles = [angle] * 64
        self.slider.set(angle)
        self.angle_display.config(text=f"{angle}°")
        if self.on_angle_change:
            self.on_angle_change(self.current_angles)
    
    def _start_wave(self):
        threading.Thread(target=self._wave_animation, daemon=True).start()
    
    def _wave_animation(self):
        for frame in range(60):
            angles = []
            for i in range(64):
                row = i // 8
                col = i % 8
                wave = math.sin((frame + col + row) * 0.3) * 45 + 90
                angles.append(int(wave))
            
            self.current_angles = angles
            if self.on_angle_change:
                self.on_angle_change(angles)
            time.sleep(0.05)
        
        # Update UI on main thread
        self.after(0, lambda: self._set_angle(90))
    
    def _test_motors(self):
        """Toggle continuous motor test"""
        if hasattr(self, 'testing') and self.testing:
            # Stop testing
            self.testing = False
            self.test_btn.text = "🔧 Test"
            self.test_btn.default_bg = COLORS['success']
            self.test_btn.current_bg = COLORS['success']
            self.test_btn._draw()
        else:
            # Start testing
            self.testing = True
            self.test_btn.text = "⏹ Stop"
            self.test_btn.default_bg = COLORS['error']
            self.test_btn.current_bg = COLORS['error']
            self.test_btn._draw()
            threading.Thread(target=self._test_animation, daemon=True).start()
    
    def _test_animation(self):
        """Sweep all motors continuously: 90 -> 0 -> 180 -> 90 (loop)"""
        while hasattr(self, 'testing') and self.testing:
            # Go to 0
            for angle in range(90, -1, -5):
                if not self.testing:
                    break
                self.current_angles = [angle] * 64
                if self.on_angle_change:
                    self.on_angle_change(self.current_angles)
                time.sleep(0.05)
            
            if not self.testing:
                break
            time.sleep(0.3)
            
            # Go to 180
            for angle in range(0, 181, 5):
                if not self.testing:
                    break
                self.current_angles = [angle] * 64
                if self.on_angle_change:
                    self.on_angle_change(self.current_angles)
                time.sleep(0.05)
            
            if not self.testing:
                break
            time.sleep(0.3)
            
            # Back to 90
            for angle in range(180, 89, -5):
                if not self.testing:
                    break
                self.current_angles = [angle] * 64
                if self.on_angle_change:
                    self.on_angle_change(self.current_angles)
                time.sleep(0.05)
            
            time.sleep(0.3)
        
        # Reset to center when stopped (main thread)
        self.after(0, lambda: self._set_angle(90))
