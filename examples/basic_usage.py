#!/usr/bin/env python3
"""
Basic PyCarPlay Example

This example shows how to embed PyCarPlay widget in a simple window.
The widget is a COMPONENT, not a standalone window.
"""

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
import sys

# Import from installed package
from pycarplay import CarPlayWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CarPlay Application")
        
        # Create central widget with layout
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create and add CarPlay widget
        self.carplay = CarPlayWidget()
        layout.addWidget(self.carplay)
        
        # Set central widget
        self.setCentralWidget(central)
        
        # Resize to match CarPlay video dimensions
        self.resize(1280, 720)

def main():
    app = QApplication(sys.argv)
    
    # Create main window with embedded CarPlay
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
