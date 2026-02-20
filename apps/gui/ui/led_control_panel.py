import tkinter as tk
from tkinter import ttk
import numpy as np
import cv2
import threading
from .theme import COLORS
from .widgets import ModernButton

class LEDControlPanel(tk.Frame):
    """Control panel for LED patterns and test modes"""
    def __init__(self, parent, on_frame_generated=None, main_log=None, **kwargs):
        super().__init__(parent, bg=COLORS['bg_medium'], **kwargs)
        
        self.on_frame_generated = on_frame_generated # Callback(frame_32x64)
        self.on_sequential_step = None # Callback(step_name)
        self.on_capture_done = None    # Callback() - fired when capture finishes
        self.main_log = main_log
        self.test_mode = False
        self.scroll_active = False
        self.capture_mode = False      # True during diagnostic capture
        self.scroll_text_var = tk.StringVar(value="HOOKKAPANI STUDIO")
        
        self._create_widgets()
        
    def _create_widgets(self):
        # Title
        tk.Label(self, text="🎨 PATTERNS", 
                bg=COLORS['bg_medium'], fg=COLORS['text_primary'],
                font=('Segoe UI', 10, 'bold')).pack(pady=(8, 5))
        
        # Test Mode Toggle
        self.mode_frame = tk.Frame(self, bg=COLORS['bg_medium'])
        self.mode_frame.pack(fill='x', padx=5, pady=2)
        
        self.live_btn = ModernButton(self.mode_frame, text="👤 Live", 
                                     command=self._set_live_mode,
                                     bg=COLORS['success'], width=80, height=26)
        self.live_btn.pack(side='left', padx=2, expand=True)
        
        self.test_btn = ModernButton(self.mode_frame, text="🔧 Test", 
                                     command=self._set_test_mode,
                                     bg=COLORS['bg_light'], width=80, height=26)
        self.test_btn.pack(side='left', padx=2, expand=True)

        self.cal_btn = ModernButton(self.mode_frame, text="🎯 Auto", 
                                     command=self._start_calibration,
                                     bg=COLORS['warning'], width=70, height=26)
        self.cal_btn.pack(side='left', padx=2, expand=True)

        self.man_btn = ModernButton(self.mode_frame, text="🖱️ Manual", 
                                     command=self._start_manual_calibration,
                                     bg='#b23b8c', width=70, height=26)
        self.man_btn.pack(side='left', padx=2, expand=True)

        # PATTERN GRID
        grid_frame = tk.Frame(self, bg=COLORS['bg_medium'])
        grid_frame.pack(fill='x', padx=5, pady=5)
        
        all_patterns = [
            ("Sequential", "sequential", "#0081a7"),
            ("Panel ID", "panels", "#0f3460"),
            ("White", "calib_white", "#e94560"), # Red for calibration
            ("Grid", "grid", "#0f3460"), 
            ("Checker", "checker", "#0f3460"), 
            ("Corners", "corners", "#0f3460"),
            ("Reset", "reset", "#444"),
            ("↑ Up", "arrow_up", "#16213e"),
            ("↓ Down", "arrow_down", "#16213e"),
            ("← Left", "arrow_left", "#16213e"),
            ("→ Right", "arrow_right", "#16213e")
        ]
        
        for i, (txt, cmd, bcolor) in enumerate(all_patterns):
            row = i // 3
            col = i % 3
            btn = tk.Button(grid_frame, text=txt, 
                           command=lambda c=cmd: self._run_pattern(c),
                           bg=bcolor, fg='white', bd=0, 
                           font=('Segoe UI', 7, 'bold'), 
                           pady=4, width=8)
            btn.grid(row=row, column=col, padx=2, pady=2, sticky='nsew')
            
        for i in range(3):
            grid_frame.grid_columnconfigure(i, weight=1)

        # Scrolling Text
        tk.Label(self, text="📜 TEXT SCROLLER", bg=COLORS['bg_medium'], fg=COLORS['text_secondary'],
                font=('Segoe UI', 8, 'bold')).pack(anchor='w', padx=10, pady=(5,0))
        
        s_frame = tk.Frame(self, bg=COLORS['bg_medium'])
        s_frame.pack(fill='x', padx=5, pady=2)
        
        tk.Entry(s_frame, textvariable=self.scroll_text_var, width=15, 
                bg=COLORS['bg_dark'], fg='white', bd=0, insertbackground='white').pack(side='left', padx=2, fill='x', expand=True)
        tk.Button(s_frame, text="▶", command=self._start_scroll,
                 bg=COLORS['success'], fg='white', bd=0, width=3).pack(side='left', padx=1)
        tk.Button(s_frame, text="■", command=self._stop_scroll,
                 bg=COLORS['error'], fg='white', bd=0, width=3).pack(side='left', padx=1)

    def _set_live_mode(self):
        self.test_mode = False
        self.scroll_active = False
        self.live_btn.set_color(COLORS['success']) # Green
        self.test_btn.set_color(COLORS['bg_light']) # Gray
        if self.main_log: self.main_log("Switched to LIVE mode")

    def _set_test_mode(self):
        self.test_mode = True
        self.live_btn.set_color(COLORS['bg_light'])
        self.test_btn.set_color(COLORS['warning']) # Orange
        if self.main_log: self.main_log("Switched to TEST mode")

    def _start_calibration(self):
        # Parent will handle overriding
        pass

    def _start_manual_calibration(self):
        # Parent will handle overriding
        pass

    def _run_pattern(self, name):
        """Run a pattern (static or animated)"""
        self._set_test_mode()
        self.scroll_active = False # Stop text if running
        
        if name == "sequential":
            self.scroll_active = True # Use same flag for pattern loop
            threading.Thread(target=self._sequential_loop, daemon=True).start()
            return
            
        frame = self._generate_pattern(name)
        if self.on_frame_generated:
            self.on_frame_generated(frame)
        if self.main_log: self.main_log(f"Showing pattern: {name}")

    def _sequential_loop(self):
        """Cycle through panel pairs (Rows) with downward arrows.
        
        In capture_mode: runs exactly once through 5 steps, with proper
        settle time before firing the screenshot callback.
        In normal mode: loops forever at 5s intervals.
        """
        import time
        step = 1
        one_pass_done = False
        
        while self.scroll_active and self.test_mode:
            # If we already completed one full pass in capture mode, stop
            if self.capture_mode and one_pass_done:
                break
            
            frame = np.zeros((64, 32), dtype=np.uint8)
            step_name = None
            
            if step <= 4:
                # Pairs (Rows): 1+2, 3+4, 5+6, 7+8
                row_idx = step - 1
                y1, y2 = row_idx * 16, (row_idx + 1) * 16
                p1, p2 = step*2 - 1, step*2
                
                # Highlight Row
                frame[y1:y2, 0:32] = 160
                
                # Draw Downward Arrow in the row
                cv2.line(frame, (16, y1+2), (16, y2-4), 255, 2)
                cv2.line(frame, (16, y2-4), (10, y2-8), 255, 2)
                cv2.line(frame, (16, y2-4), (22, y2-8), 255, 2)
                
                # Label Panels
                cv2.putText(frame, str(p1), (4, y1+12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, 255, 1)
                cv2.putText(frame, str(p2), (24, y1+12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, 255, 1)
                
                step_name = f"Panels_{p1}_{p2}"
                if self.main_log: self.main_log(f"Testing Row {step} (Panels {p1} & {p2}) - Arrow DOWN")
            else:
                # All panels
                frame.fill(255)
                cv2.putText(frame, "ALL OK", (4, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.4, 0, 1)
                step_name = "All_Panels"
                if self.main_log: self.main_log("Testing ALL Panels")

            # 1. SEND the pattern to hardware first
            if self.on_frame_generated:
                self.on_frame_generated(frame)
            
            if self.capture_mode:
                # 2. WAIT for LEDs to physically light up + camera to see it
                time.sleep(2.0)
                # 3. NOW fire the callback to take the screenshot
                if self.on_sequential_step:
                    self.on_sequential_step(step_name)
                # 4. Wait remaining time before next step
                time.sleep(3.0)
            else:
                # Normal browsing mode — just fire callback and wait
                if self.on_sequential_step:
                    self.on_sequential_step(step_name)
                time.sleep(5.0)
            
            step += 1
            if step > 5:
                if self.capture_mode:
                    one_pass_done = True
                else:
                    step = 1
        
        # Signal capture completion
        if self.capture_mode:
            self.capture_mode = False
            if self.on_capture_done:
                self.on_capture_done()

    def update_ber(self, ber):
        """Update Bit Error Rate display"""
        # Create label if not exists
        if not hasattr(self, 'ber_label'):
            self.ber_label = tk.Label(self.mode_frame, text="BER: 0%", 
                                      bg=COLORS['bg_light'], fg='white', font=('Segoe UI', 8))
            self.ber_label.pack(side='right', padx=5)
            
        # Color code
        color = '#00ff00' if ber < 0.05 else '#ffff00' if ber < 0.15 else '#ff0000'
        self.ber_label.config(text=f"BER: {ber*100:.1f}%", fg=color)

    def _start_scroll(self):
        self._set_test_mode()
        self.scroll_active = True
        threading.Thread(target=self._scroll_loop, daemon=True).start()

    def _stop_scroll(self):
        self.scroll_active = False

    def _scroll_loop(self):
        pos = 0
        text = self.scroll_text_var.get()
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, th), _ = cv2.getTextSize(text, font, 0.5, 1)
        width = 32
        full_w = tw + width * 2
        
        canvas = np.zeros((64, full_w), dtype=np.uint8)
        cv2.putText(canvas, text, (width, 32 + th//2), font, 0.5, 255, 1)
        
        while self.scroll_active and self.test_mode:
            offset = pos % (tw + width)
            frame = canvas[:, offset:offset+width]
            
            # Pad if needed
            if frame.shape[1] < width:
                padded = np.zeros((64, width), dtype=np.uint8)
                padded[:, :frame.shape[1]] = frame
                frame = padded
            
            if self.on_frame_generated:
                self.on_frame_generated(frame)
            
            pos += 1
            import time
            time.sleep(0.05)
            
    def _generate_pattern(self, name):
        frame = np.zeros((64, 32), dtype=np.uint8)
        
        if name == 'reset':
            return frame # All zeros
        
        if name == 'grid':
            frame[0::16, :] = 255
            frame[:, 0::16] = 255
            frame[-1, :] = 255
            frame[:, -1] = 255
        elif name == 'checker':
            for y in range(0, 64, 4):
                for x in range(0, 32, 4):
                    if ((x//4) + (y//4)) % 2 == 0:
                        frame[y:y+4, x:x+4] = 255
        elif name == 'corners':
            frame[0:2, 0:2] = 255
            frame[0:2, -2:] = 255
            frame[-2:, 0:2] = 255
            frame[-2:, -2:] = 255
        elif name == 'panels':
            # Draw panel numbers
            panels = [(1, 4, 12), (2, 18, 12), (3, 4, 28), (4, 18, 28),
                      (5, 4, 44), (6, 18, 44), (7, 4, 60), (8, 18, 60)]
            font = cv2.FONT_HERSHEY_SIMPLEX
            for num, x, y in panels:
                cv2.putText(frame, str(num), (x, y), font, 0.7, 255, 2)
        elif name == 'calib_white':
            frame[:, :] = 255  # All LEDs full brightness
        elif name.startswith('arrow'):
            cx, cy = 16, 32
            if 'up' in name:
                pts = np.array([[cx, cy-10], [cx-8, cy+5], [cx+8, cy+5]])
                cv2.fillPoly(frame, [pts], 255)
            elif 'down' in name:
                pts = np.array([[cx, cy+10], [cx-8, cy-5], [cx+8, cy-5]])
                cv2.fillPoly(frame, [pts], 255)
            elif 'left' in name:
                pts = np.array([[cx-10, cy], [cx+5, cy-8], [cx+5, cy+8]])
                cv2.fillPoly(frame, [pts], 255)
            elif 'right' in name:
                pts = np.array([[cx+10, cy], [cx-5, cy-8], [cx-5, cy+8]])
                cv2.fillPoly(frame, [pts], 255)

        return frame
