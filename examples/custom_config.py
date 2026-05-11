#!/usr/bin/env python3
"""
Custom Configuration Example

This example shows how to customize CarPlay settings
and embed the widget in a window.
"""

from pathlib import Path
import sys

# Allow running examples directly from repo root without installing package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout

from pycarplay import CarPlayWidget
from config import config

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Create central widget with layout
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create CarPlay widget with custom config
        self.carplay = CarPlayWidget(config=config)
        layout.addWidget(self.carplay)
        
        self.setCentralWidget(central)
        self.setWindowTitle("My Custom CarPlay App")
        self.resize(1920, 1080)
        
        # Manual connect after window is shown
        # (since auto_connect = False)
        print("Window ready. Call carplay.connect() to connect manually")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    # Manual connect example (optional)
    # window.carplay.connect()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
