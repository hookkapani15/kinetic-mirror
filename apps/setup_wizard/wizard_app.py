#!/usr/bin/env python3
"""
Hardware Setup Wizard - Main GUI
Step-by-step diagnostic wizard for hardware setup.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import List, Optional

# Import stages
from .stages.base_stage import BaseStage, StageStatus, StageResult
from .stages.stage_dependencies import DependenciesStage
from .stages.stage_camera import CameraStage
from .stages.stage_esp32 import ESP32Stage
from .stages.stage_led_power import LEDPowerStage
from .stages.stage_led_mapping import LEDMappingStage
from .stages.stage_motors import MotorStage


class SetupWizard:
    """Main Setup Wizard GUI Application."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("🔧 Mirror Body - Hardware Setup Wizard")
        self.root.geometry("700x550")
        self.root.resizable(False, False)
        
        # State
        self.current_stage_idx = 0
        self.detected_port = None
        self.stages: List[BaseStage] = []
        self.running = False
        
        self._init_stages()
        self._create_widgets()
        
    def _init_stages(self):
        """Initialize all diagnostic stages."""
        self.stages = [
            DependenciesStage(),
            CameraStage(),
            ESP32Stage(),
            LEDPowerStage(),
            LEDMappingStage(),
            MotorStage()
        ]
    
    def _create_widgets(self):
        """Create the wizard GUI."""
        # Header
        header = ttk.Frame(self.root, padding=10)
        header.pack(fill=tk.X)
        
        ttk.Label(header, text="🔧 Hardware Setup Wizard", 
                  font=("Arial", 16, "bold")).pack(side=tk.LEFT)
        
        # Progress
        progress_frame = ttk.Frame(self.root, padding=10)
        progress_frame.pack(fill=tk.X)
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.progress_var, 
            maximum=len(self.stages), length=650
        )
        self.progress_bar.pack(fill=tk.X)
        
        self.progress_label = ttk.Label(
            progress_frame, 
            text=f"Stage 1/{len(self.stages)}: {self.stages[0].name}"
        )
        self.progress_label.pack(pady=5)
        
        # Main content area
        self.content_frame = ttk.LabelFrame(
            self.root, text="", padding=15
        )
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Stage title
        self.stage_title = ttk.Label(
            self.content_frame, 
            text=self.stages[0].name,
            font=("Arial", 14, "bold")
        )
        self.stage_title.pack(anchor=tk.W)
        
        self.stage_desc = ttk.Label(
            self.content_frame,
            text=self.stages[0].description
        )
        self.stage_desc.pack(anchor=tk.W, pady=(0, 10))
        
        # Checks list (scrollable)
        checks_container = ttk.Frame(self.content_frame)
        checks_container.pack(fill=tk.BOTH, expand=True)
        
        self.checks_text = tk.Text(
            checks_container, height=12, wrap=tk.WORD,
            font=("Consolas", 10), state=tk.DISABLED
        )
        self.checks_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(checks_container, command=self.checks_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.checks_text.config(yscrollcommand=scrollbar.set)
        
        # Fix instructions area
        self.fix_frame = ttk.LabelFrame(self.content_frame, text="💡 How to Fix", padding=10)
        self.fix_frame.pack(fill=tk.X, pady=10)
        self.fix_frame.pack_forget()  # Hidden by default
        
        self.fix_text = tk.Text(
            self.fix_frame, height=5, wrap=tk.WORD,
            font=("Arial", 10), state=tk.DISABLED, bg="#fff9e6"
        )
        self.fix_text.pack(fill=tk.X)
        
        # Buttons
        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill=tk.X)
        
        self.back_btn = ttk.Button(btn_frame, text="◀ Back", command=self._prev_stage)
        self.back_btn.pack(side=tk.LEFT, padx=5)
        self.back_btn.config(state=tk.DISABLED)
        
        self.skip_btn = ttk.Button(btn_frame, text="Skip ▶", command=self._skip_stage)
        self.skip_btn.pack(side=tk.LEFT, padx=5)
        
        self.run_btn = ttk.Button(btn_frame, text="▶ Run Test", command=self._run_stage)
        self.run_btn.pack(side=tk.RIGHT, padx=5)
        
        self.next_btn = ttk.Button(btn_frame, text="Next ▶", command=self._next_stage)
        self.next_btn.pack(side=tk.RIGHT, padx=5)
        self.next_btn.config(state=tk.DISABLED)
    
    def _update_ui(self):
        """Update UI for current stage."""
        stage = self.stages[self.current_stage_idx]
        
        # Update progress
        self.progress_var.set(self.current_stage_idx)
        self.progress_label.config(
            text=f"Stage {self.current_stage_idx + 1}/{len(self.stages)}: {stage.name}"
        )
        
        # Update content
        self.stage_title.config(text=stage.name)
        self.stage_desc.config(text=stage.description)
        
        # Clear checks
        self.checks_text.config(state=tk.NORMAL)
        self.checks_text.delete(1.0, tk.END)
        self.checks_text.config(state=tk.DISABLED)
        
        # Hide fix frame
        self.fix_frame.pack_forget()
        
        # Update buttons
        self.back_btn.config(state=tk.NORMAL if self.current_stage_idx > 0 else tk.DISABLED)
        self.next_btn.config(state=tk.DISABLED)
        self.run_btn.config(state=tk.NORMAL)
    
    def _add_check_result(self, name: str, passed: bool, message: str):
        """Add a check result to the display."""
        icon = "✅" if passed else "❌"
        self.checks_text.config(state=tk.NORMAL)
        self.checks_text.insert(tk.END, f"{icon} {name}: {message}\n")
        self.checks_text.see(tk.END)
        self.checks_text.config(state=tk.DISABLED)
        self.root.update()
    
    def _show_fix_instructions(self, instructions: List[str]):
        """Show fix instructions."""
        if not instructions:
            return
        
        self.fix_frame.pack(fill=tk.X, pady=10)
        self.fix_text.config(state=tk.NORMAL)
        self.fix_text.delete(1.0, tk.END)
        for i, instr in enumerate(instructions, 1):
            if instr:
                self.fix_text.insert(tk.END, f"{i}. {instr}\n")
        self.fix_text.config(state=tk.DISABLED)
    
    def _run_stage(self):
        """Run the current stage's tests."""
        if self.running:
            return
        
        self.running = True
        self.run_btn.config(state=tk.DISABLED)
        self.skip_btn.config(state=tk.DISABLED)
        
        # Clear previous results
        self.checks_text.config(state=tk.NORMAL)
        self.checks_text.delete(1.0, tk.END)
        self.checks_text.config(state=tk.DISABLED)
        self.fix_frame.pack_forget()
        
        # Run in thread
        def run_thread():
            stage = self.stages[self.current_stage_idx]
            
            # Pass detected port to hardware stages
            if hasattr(stage, 'port') and self.detected_port:
                stage.port = self.detected_port
            
            # Run with callback
            result = stage.run(callback=lambda n, p, m: 
                self.root.after(0, self._add_check_result, n, p, m)
            )
            
            # Store detected port from ESP32 stage
            if isinstance(stage, ESP32Stage) and stage.detected_port:
                self.detected_port = stage.detected_port
            
            # Update UI on main thread
            self.root.after(0, self._on_stage_complete, result)
        
        threading.Thread(target=run_thread, daemon=True).start()
    
    def _on_stage_complete(self, result: StageResult):
        """Handle stage completion."""
        self.running = False
        self.run_btn.config(state=tk.NORMAL)
        self.skip_btn.config(state=tk.NORMAL)
        
        if result.passed:
            self.next_btn.config(state=tk.NORMAL)
            self._add_check_result("", True, "Stage passed! Click Next to continue.")
        else:
            # Show fix instructions for failed checks
            all_fixes = []
            for check in result.failed_checks:
                all_fixes.extend(check.fix_instructions)
            
            if all_fixes:
                self._show_fix_instructions(all_fixes)
            
            self._add_check_result("", False, "Some checks failed. Fix issues and retry.")
    
    def _next_stage(self):
        """Move to next stage."""
        if self.current_stage_idx < len(self.stages) - 1:
            self.current_stage_idx += 1
            self._update_ui()
        else:
            # All stages complete
            self._on_wizard_complete()
    
    def _prev_stage(self):
        """Move to previous stage."""
        if self.current_stage_idx > 0:
            self.current_stage_idx -= 1
            self._update_ui()
    
    def _skip_stage(self):
        """Skip current stage."""
        self.stages[self.current_stage_idx].status = StageStatus.SKIPPED
        self._next_stage()
    
    def _on_wizard_complete(self):
        """Handle wizard completion."""
        messagebox.showinfo(
            "Setup Complete!",
            "🎉 All hardware tests passed!\n\n"
            "Your system is ready to use.\n"
            "Run 'python main.py' to start the simulation."
        )
        self.root.destroy()


def main():
    """Entry point for the setup wizard."""
    root = tk.Tk()
    app = SetupWizard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
