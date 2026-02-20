import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import serial
import serial.tools.list_ports
import os
import sys
import subprocess

from .theme import COLORS
from .widgets import ModernButton
from core.config import (
    FIRMWARE_BIN_ESP32, FIRMWARE_BIN_ESP32S3, 
    FLASH_LAYOUTS, has_any_firmware_binary,
    ESP32_S3_IDENTIFIERS
)

class ConnectionPanel(tk.Frame):
    """ESP32-S3 connection panel with firmware flashing"""
    def __init__(self, parent, on_connect=None, on_disconnect=None, main_log=None, **kwargs):
        super().__init__(parent, bg=COLORS['bg_medium'], **kwargs)
        
        self.on_connect_callback = on_connect
        self.on_disconnect_callback = on_disconnect
        self.main_log = main_log  # Callback to main system log
        self.serial_port = None
        self.connected = False
        self.detected_port = None
        self.flashing = False
    
        # UI Attributes (declared here for linter)
        self.port_var = tk.StringVar()
        self.port_combo = None
        self.device_info = None
        self.status_indicator = None
        self.status_label = None
        self.connect_btn = None
        self.fw_status = None
        self.flash_btn = None
        self.progress_var = tk.DoubleVar()
        self.progress = None
        self.flash_log = None
    
        self._create_widgets()
        self.monitor_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_connection, daemon=True)
        self.monitor_thread.start()

    def _create_widgets(self):
        # Header Row: Port + Refresh + Connect + Flash
        header_frame = tk.Frame(self, bg=COLORS['bg_medium'])
        header_frame.pack(fill='x', padx=5, pady=5)
        
        tk.Label(header_frame, text="🔌", bg=COLORS['bg_medium'], 
                 fg=COLORS['text_primary'], font=('Segoe UI', 10)).pack(side='left', padx=(2, 5))
        
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(header_frame, textvariable=self.port_var, 
                                       width=12, state='readonly')
        self.port_combo.pack(side='left', padx=2)
        
        refresh_btn = tk.Button(header_frame, text="⟳", command=self._refresh_ports,
                               bg=COLORS['bg_light'], fg=COLORS['text_primary'],
                               font=('Segoe UI', 8), bd=0, padx=4, pady=1)
        refresh_btn.pack(side='left', padx=2)
        
        # Connect button
        self.connect_btn = ModernButton(header_frame, text="Connect", 
                                        command=self._toggle_connection,
                                        width=70, height=24,
                                        bg=COLORS['success'])
        self.connect_btn.pack(side='left', padx=2)
        
        # Flash button
        self.flash_btn = ModernButton(header_frame, text="🔥 Flash", 
                  command=self._start_flash_instructions,
                  width=65, height=24,
                  bg=COLORS['warning'])
        self.flash_btn.pack(side='left', padx=2)

        # Status & Info Row
        info_row = tk.Frame(self, bg=COLORS['bg_medium'])
        info_row.pack(fill='x', padx=5, pady=(0, 2))
        
        self.status_indicator = tk.Canvas(info_row, width=8, height=8, 
                                          bg=COLORS['bg_medium'], highlightthickness=0)
        self.status_indicator.pack(side='left', padx=(5, 0))
        self._draw_status_dot(False)
        
        self.status_label = tk.Label(info_row, text="Disconnected", 
                                     bg=COLORS['bg_medium'], fg=COLORS['text_secondary'],
                                     font=('Segoe UI', 8))
        self.status_label.pack(side='left', padx=(5, 10))
        
        self.device_info = tk.Label(info_row, text="", bg=COLORS['bg_medium'], 
                                   fg=COLORS['text_secondary'], font=('Segoe UI', 7))
        self.device_info.pack(side='left')

        # Firmware status (compact)
        self.fw_status = tk.Label(self, text="", bg=COLORS['bg_medium'], 
                     fg=COLORS['text_secondary'], font=('Segoe UI', 7))
        self.fw_status.pack(pady=(0, 2))
        
        # Progress bar (hidden initially)
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(self, variable=self.progress_var, maximum=100, length=150)
        
        # Flash log (hidden initially)
        self.flash_log = tk.Text(self, height=3, width=22, bg=COLORS['bg_dark'],
                                fg=COLORS['text_secondary'], font=('Consolas', 7),
                                state='disabled')
        
        # Initial port refresh
        self._refresh_ports()
        self._check_firmware()

    def _toggle_connection(self):
        if self.connected:
            self._disconnect()
        else:
            self._connect()
    
    def _connect(self):
        port_str = self.port_var.get()
        if not port_str:
            return
        
        port = port_str.replace('★', '').strip()
        
        if port == "SIMULATOR":
            self.serial_port = None
            self.connected = True
            self._update_ui_connected(port)
            if self.on_connect_callback:
                self.on_connect_callback(None, True)
        else:
            # Disable button while connecting
            self.connect_btn.set_enabled(False)
            self.status_label.config(text="Connecting...", fg=COLORS['warning'])
            # Run connection in background to avoid blocking UI
            threading.Thread(target=self._connect_bg, args=(port,), daemon=True).start()
    
    def _connect_bg(self, port):
        """Background thread for serial connection (avoids blocking UI)"""
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                ser = serial.Serial(port=port, baudrate=460800, timeout=1, write_timeout=1.0, dsrdtr=True)
                # DTR/RTS reset sequence to properly boot ESP32
                # IMPORTANT: ESP32-S3 native USB CDC requires DTR=True for serial I/O
                ser.dtr = False
                ser.rts = False
                time.sleep(0.1)
                ser.dtr = True
                ser.rts = True
                time.sleep(0.1)
                ser.rts = False
                # Keep DTR=True! ESP32-S3 USB CDC needs it for serial communication
                time.sleep(2.0)  # Wait for ESP32 boot
                
                # Drain any boot messages
                try:
                    ser.reset_input_buffer()
                except Exception:
                    pass
                
                self.serial_port = ser
                self.connected = True
                # Update UI on main thread
                self.after(0, lambda: self._update_ui_connected(port))
                self.after(0, lambda: self.connect_btn.set_enabled(True))
                if self.on_connect_callback:
                    self.after(0, lambda: self.on_connect_callback(self.serial_port, False))
                return  # Success!
            except serial.SerialException as e:
                last_error = e
                time.sleep(0.5)  # Wait before retry
        
        # All retries failed — update UI on main thread
        error_msg = str(last_error) if last_error else "Unknown error"
        def _show_error():
            self.connect_btn.set_enabled(True)
            self.status_label.config(text="Disconnected", fg=COLORS['text_secondary'])
            if "Access is denied" in error_msg or "PermissionError" in error_msg:
                messagebox.showerror("Port Busy", 
                    f"Cannot access {port}.\n\n"
                    f"Please check:\n"
                    f"• Close Arduino IDE or Serial Monitor\n"
                    f"• Close any other program using {port}\n"
                    f"• Unplug and replug the USB cable\n\n"
                    f"Error: {error_msg}")
            else:
                messagebox.showerror("Connection Error", f"Failed: {error_msg}")
        self.after(0, _show_error)
    
    def _disconnect(self):
        if self.serial_port:
            try:
                self.serial_port.reset_output_buffer()
            except Exception:
                pass
            try:
                self.serial_port.close()
            except Exception:
                pass
            self.serial_port = None
        
        self.connected = False
        self._update_ui_disconnected()
        if self.on_disconnect_callback:
            self.on_disconnect_callback()
    
    def _update_ui_connected(self, port):
        self._draw_status_dot(True)
        self.status_label.config(text=f"Connected", fg=COLORS['success'])
        self.connect_btn.text = "Disconnect"
        self.connect_btn.default_bg = COLORS['error']
        self.connect_btn.current_bg = COLORS['error']
        self.connect_btn._draw()
    
    def _update_ui_disconnected(self):
        self._draw_status_dot(False)
        self.status_label.config(text="Disconnected", fg=COLORS['text_secondary'])
        self.connect_btn.text = "Connect"
        self.connect_btn.default_bg = COLORS['success']
        self.connect_btn.current_bg = COLORS['success']
        self.connect_btn._draw()

    def _check_firmware(self):
        """Check if firmware files exist"""
        if os.path.exists(FIRMWARE_BIN_ESP32S3):
            size_kb = os.path.getsize(FIRMWARE_BIN_ESP32S3) / 1024
            self.fw_status.config(text=f"✓ esp32s3 firmware.bin ({size_kb:.0f}KB)", fg=COLORS['success'])
            self.flash_btn.set_enabled(True)
        elif os.path.exists(FIRMWARE_BIN_ESP32):
            size_kb = os.path.getsize(FIRMWARE_BIN_ESP32) / 1024
            self.fw_status.config(text=f"✓ esp32 firmware.bin ({size_kb:.0f}KB)", fg=COLORS['success'])
            self.flash_btn.set_enabled(True)
        else:
            self.fw_status.config(text="✗ firmware.bin not found (esp32/esp32s3)", fg=COLORS['error'])
            self.flash_btn.set_enabled(False)

    def _draw_status_dot(self, connected):
        self.status_indicator.delete('all')
        color = COLORS['success'] if connected else COLORS['error']
        self.status_indicator.create_oval(1, 1, 9, 9, fill=color, outline='')

    def _monitor_connection(self):
        """Monitor connection status and port availability"""
        last_port_count = 0
        
        while self.monitor_running:
            try:
                # Get current ports
                current_ports = serial.tools.list_ports.comports()
                current_port_names = [p.device for p in current_ports]
                
                # 1. Check if connected port still exists (Auto-disconnect)
                if self.connected and self.serial_port:
                    connected_port = self.serial_port.port
                    if connected_port not in current_port_names:
                        self.after(0, lambda: self._handle_force_disconnect("Device disconnected"))
                
                # 2. Check for port changes (Auto-refresh)
                if len(current_ports) != last_port_count:
                    # Only refresh if dropdown is not open/active? 
                    # Hard to detect, but safe to update 'values'
                    self.after(0, self._refresh_ports)
                    last_port_count = len(current_ports)
                
            except Exception as e:
                print(f"Monitor error: {e}")
            
            time.sleep(1.0)

    def _handle_force_disconnect(self, reason):
        """Force disconnect and switch to simulation"""
        if not self.connected:
            return
            
        self._disconnect()
        messagebox.showwarning("Connection Lost", f"{reason}\nSwitching to Simulation Mode.")
        
        # Auto-switch to simulator
        self.port_combo.set("SIMULATOR")
        self._toggle_connection()

    def _start_flash_instructions(self):
        """Simplified flash process - directly start flashing"""
        port_str = self.port_var.get()
        
        if not port_str or port_str == "SIMULATOR":
            messagebox.showerror("Flash Error", "Cannot flash SIMULATOR.\nPlease select a real ESP32 port.")
            return
            
        if "No ports" in port_str:
            messagebox.showerror("Flash Error", "No COM port available.\nPlease connect your ESP32.")
            return

        port = port_str.replace('★', '').strip()
        
        # Check at least one firmware build exists (ESP32 or ESP32-S3)
        if not has_any_firmware_binary():
            messagebox.showerror(
                "Flash Error",
                "No firmware binary found.\n\nPlease build first: pio run -e esp32 or pio run -e esp32s3",
            )
            return
        
        # Disconnect if connected to this port
        if self.connected and self.serial_port:
            try:
                if self.serial_port.port == port:
                    self._disconnect()
                    time.sleep(0.3)
            except:
                pass
        
        # Confirm
        result = messagebox.askyesno("Flash Firmware", 
            f"Flash firmware to {port}?\n\n"
            f"IMPORTANT: Put ESP32 into download mode:\n"
            f"1. Hold BOOT button\n"
            f"2. Press RESET button\n"
            f"3. Release RESET, then BOOT\n\n"
            f"Ready to flash?")
        
        if not result:
            return
        
        # Show progress UI
        self.progress.pack(pady=5)
        self.flash_log.pack(pady=5, padx=5, fill='x')
        self.flash_btn.set_enabled(False)
        self.connect_btn.set_enabled(False)
        
        # Start flash in background thread
        self.flashing = True
        threading.Thread(target=self._do_flash, args=(port,), daemon=True).start()

    def _do_flash(self, port):
        """Perform the actual firmware flash with auto-detection"""
        try:
            self._log_flash("=" * 40)
            self._log_flash("STARTING FLASH PROCESS")
            self._log_flash("=" * 40)
            self.progress_var.set(5)
            
            # Log firmware path
            self._log_flash(f"Port: {port}")
            self._log_flash(f"ESP32 firmware exists: {os.path.exists(FIRMWARE_BIN_ESP32)}")
            self._log_flash(f"ESP32-S3 firmware exists: {os.path.exists(FIRMWARE_BIN_ESP32S3)}")
            
            # Setup esptool
            esptool_cmd = [sys.executable, '-m', 'esptool']
            try:
                import esptool
                self._log_flash("esptool: installed ✓")
            except ImportError:
                self._log_flash("Installing esptool...")
                subprocess.run([sys.executable, '-m', 'pip', 'install', 'esptool', '-q'], capture_output=True)
            
            # AUTO-DETECT chip type using esptool
            self._log_flash("Auto-detecting chip type...")
            detect_cmd = esptool_cmd + ['--port', port, 'chip_id']
            self._log_flash(f"Running: {' '.join(detect_cmd)}")
            
            detect_result = subprocess.run(detect_cmd, capture_output=True, text=True, timeout=30)
            detect_output = detect_result.stdout + detect_result.stderr
            self._log_flash(f"Chip detect output:")
            for line in detect_output.split('\n'):
                if line.strip():
                    self._log_flash(f"  {line.strip()}")
            
            # Parse chip type from detection
            chip_type = 'esp32'  # Default
            
            if 'esp32-s3' in detect_output.lower() or 'esp32s3' in detect_output.lower():
                chip_type = 'esp32s3'
                self._log_flash("✓ Detected: ESP32-S3")
            elif 'esp32' in detect_output.lower():
                chip_type = 'esp32'
                self._log_flash("✓ Detected: ESP32 (regular)")
            else:
                self._log_flash("⚠ Could not detect chip, using ESP32 default")
            
            artifacts = FLASH_LAYOUTS.get(chip_type, FLASH_LAYOUTS['esp32'])
            flash_binary = artifacts['firmware']
            bootloader_binary = artifacts['bootloader']
            partitions_binary = artifacts['partitions']

            # Check if firmware exists for detected chip
            if not os.path.exists(flash_binary):
                self._log_flash(f"✗ Firmware not found: {flash_binary}")
                messagebox.showerror("Error", f"Firmware for {chip_type.upper()} not found.\n\nBuild it using: pio run -e {chip_type}")
                return
            
            self.progress_var.set(20)
            
            size_kb = os.path.getsize(flash_binary) / 1024
            self._log_flash(f"Using firmware: {flash_binary}")
            self._log_flash(f"Firmware size: {size_kb:.1f} KB")
            
            # Build flash command with chip-aware layout.
            cmd = esptool_cmd + [
                '--chip', chip_type,
                '--port', port,
                '--baud', '115200',  # Lower baud for reliability
                '--before', 'default_reset',
                '--after', 'hard_reset',
                '--no-stub',  # Don't use stub loader (more compatible)
                'write_flash',
                '--flash_mode', 'dio',
                '--flash_freq', '40m',
                '--flash_size', 'detect',
            ]

            has_full_image = os.path.exists(bootloader_binary) and os.path.exists(partitions_binary)
            if has_full_image:
                cmd += [
                    artifacts['bootloader_addr'], bootloader_binary,
                    artifacts['partitions_addr'], partitions_binary,
                    artifacts['firmware_addr'], flash_binary,
                ]
                self._log_flash("Using full flash image (bootloader + partitions + firmware)")
            else:
                cmd += [artifacts['firmware_addr'], flash_binary]
                self._log_flash("Using app-only flash (firmware.bin)")
            
            # Log full command
            self._log_flash("-" * 40)
            self._log_flash("EXECUTING COMMAND:")
            cmd_str = ' '.join(cmd)
            self._log_flash(cmd_str[:100])
            if len(cmd_str) > 100:
                self._log_flash(cmd_str[100:])
            self._log_flash("-" * 40)
            
            self.progress_var.set(30)
            self._log_flash("Running esptool...")
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            
            for line in process.stdout:
                line = line.strip()
                if line:
                    # Log FULL line, not truncated
                    self._log_flash(line)
                    if 'Writing' in line:
                        self.progress_var.set(50)
                    if 'Hash of data' in line:
                        self.progress_var.set(80)
            
            process.wait()
            
            self._log_flash(f"Exit code: {process.returncode}")
            
            if process.returncode == 0:
                self.progress_var.set(100)
                self._log_flash("=" * 40)
                self._log_flash("✓ FLASH SUCCESS!")
                self._log_flash("=" * 40)
                messagebox.showinfo("Success", f"Flashed {chip_type.upper()} successfully!\n\nDevice will restart.")
            else:
                self._log_flash("=" * 40)
                self._log_flash("✗ FLASH FAILED")
                self._log_flash("=" * 40)
                messagebox.showerror("Error", "Flash failed. Check system log for details.")

        except Exception as e:
            self._log_flash(f"EXCEPTION: {e}")
            import traceback
            self._log_flash(traceback.format_exc())
            messagebox.showerror("Error", str(e))
        finally:
            self.flashing = False
            self.after(100, self._flash_complete)
    
    def _log_flash(self, text):
        """Log to flash output and main system log (thread-safe)"""
        def _do_log():
            try:
                self.flash_log.config(state='normal')
                self.flash_log.insert('end', text + '\n')
                self.flash_log.see('end')
                self.flash_log.config(state='disabled')
            except Exception:
                pass
        try:
            self.after(0, _do_log)
            if self.main_log:
                self.after(0, lambda: self.main_log(f"[FLASH] {text}"))
        except Exception:
            print(f"[FLASH] {text}")
    
    def _flash_complete(self):
        """Clean up after flash"""
        self.flash_btn.set_enabled(True)
        self.connect_btn.set_enabled(True)
        self.after(3000, self._hide_flash_ui)
        self._refresh_ports()
    
    def _hide_flash_ui(self):
        """Hide flash progress UI"""
        self.progress_var.set(0)
        self.progress.pack_forget()
        self.flash_log.pack_forget()
        self.flash_log.config(state='normal')
        self.flash_log.delete('1.0', 'end')
        self.flash_log.config(state='disabled')
    
    def _refresh_ports(self):
        ports = list(serial.tools.list_ports.comports())
        port_list = []
        
        for p in ports:
            port_info = p.device
            is_esp = False
            
            if p.vid and p.pid:
                for vid, pid in ESP32_S3_IDENTIFIERS:
                    if p.vid == vid and p.pid == pid:
                        is_esp = True
                        break
            
            desc = f"{port_info}"
            if is_esp:
                desc += " ★" # Mark as likely candidate
            port_list.append(desc)
        
        # Always add SIMULATOR option
        port_list.append("SIMULATOR")
            
        if port_list:
            self.port_combo['values'] = port_list
            # Select first prioritized port (ESP device)
            for p in port_list:
                if "★" in p:
                    self.port_combo.set(p)
                    break
            else:
                # Default to first real port or SIMULATOR
                self.port_combo.set(port_list[0])
        else:
            self.port_combo['values'] = ["SIMULATOR"]
            self.port_combo.set("SIMULATOR")
