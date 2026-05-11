#!/usr/bin/env python3
"""
Basic PyCarPlay Example

This example shows how to embed PyCarPlay widget in a simple window.
The widget is a COMPONENT, not a standalone window.
"""

from pathlib import Path
import sys

# Allow running examples directly from repo root without installing package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

# Import from installed package
from pycarplay import CarPlayWidget
from config import config


def log_custom_button_press() -> None:
    print("[CustomButton] Configurable button pressed")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CarPlay Application")
        
        # Create central widget with layout
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        
        # Create and add CarPlay widget
        self.carplay = CarPlayWidget(config=config)
        self.carplay.register_custom_button_action("log_button_press", log_custom_button_press)
        layout.addWidget(self.carplay)
        self.carplay.setVisible(True)
        # Set central widget
        self.setCentralWidget(central)
        
        # Resize to match CarPlay video dimensions
        self.resize(1280, 720)
        

    def closeEvent(self, event: QCloseEvent):
        # Ensure CarPlay components stop before app process exits.
        self.carplay.cleanup()
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    
    # Create main window with embedded CarPlay
    window = MainWindow()
    app.aboutToQuit.connect(window.carplay.cleanup)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
