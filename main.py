#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DeepDel - Windows 深度清理工具
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from tkinter import ttk

def main():
    """主入口"""
    # Set DPI awareness for Windows
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    # Create main window
    root = tk.Tk()

    # Set style
    style = ttk.Style()
    style.theme_use('clam')

    # Create application
    from ui.main_window import MainWindow
    app = MainWindow(root)

    # Run
    root.mainloop()

if __name__ == '__main__':
    main()
