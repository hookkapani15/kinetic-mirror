#!/usr/bin/env python3
"""
Setup Wizard Entry Point
Run this to start the hardware setup wizard.
"""
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    from apps.setup_wizard.wizard_app import main
    main()
