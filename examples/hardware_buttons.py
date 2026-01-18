#!/usr/bin/env python3
"""
Hardware Buttons Integration Example

This example shows how to integrate PyCarPlay with physical hardware buttons
(e.g., in a car, custom device, GPIO buttons, etc.)

The widget slots can be called from ANY source:
- Hardware button interrupts
- GPIO events (Raspberry Pi)
- Serial port commands
- Network API calls
- Keyboard events
- Touch screen gestures
- etc.
"""

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import QTimer
import sys

from pycarplay import CarPlayWidget, CarPlayConfig


class HardwareButtonSimulator:
    """
    Simulates hardware buttons for demonstration.
    In real use, replace this with actual hardware input handling:
    - GPIO.add_event_detect() for Raspberry Pi
    - Serial port reader
    - CAN bus messages
    - Custom hardware API
    """
    
    def __init__(self, carplay_widget):
        self.carplay = carplay_widget
        
        # Simulate button press every 3 seconds for demo
        self.demo_timer = QTimer()
        self.demo_timer.timeout.connect(self.simulate_button_press)
        self.demo_counter = 0
    
    def start_demo(self):
        """Start simulating button presses"""
        print("\nStarting hardware button simulation...")
        print("In real use, this would be triggered by physical buttons\n")
        self.demo_timer.start(3000)  # Every 3 seconds
    
    def simulate_button_press(self):
        """Simulate different button presses"""
        buttons = [
            ("HOME", self.on_home_button),
            ("BACK", self.on_back_button),
            ("UP", self.on_up_button),
            ("DOWN", self.on_down_button),
            ("LEFT", self.on_left_button),
            ("RIGHT", self.on_right_button),
            ("OK/ENTER", self.on_ok_button),
            ("PLAY/PAUSE", self.on_play_pause_button),
        ]
        
        button_name, button_handler = buttons[self.demo_counter % len(buttons)]
        print(f"[BUTTON] Physical button pressed: {button_name}")
        button_handler()
        
        self.demo_counter += 1
    
    # === Hardware Button Handlers ===
    # These would be called by your actual hardware interrupt handlers
    
    def on_home_button(self):
        """Physical HOME button pressed"""
        # Check connection before sending command
        if self.carplay.is_phone_connected():
            self.carplay.send_home()
            print(f"   [OK] Sent HOME command (Status: {self.carplay.get_status()})")
        else:
            print(f"   [ERROR] Phone not connected (Status: {self.carplay.get_status()})")
    
    def on_back_button(self):
        """Physical BACK button pressed"""
        if self.carplay.is_phone_connected():
            self.carplay.send_back()
            print(f"   [OK] Sent BACK command")
        else:
            print(f"   [ERROR] Phone not connected")
    
    def on_up_button(self):
        """Physical UP button pressed"""
        if self.carplay.is_phone_connected():
            # Use controller for more advanced control
            controller = self.carplay.get_controller()
            controller.sendKey("up")
            print(f"   [OK] Sent UP command")
        else:
            print(f"   [ERROR] Phone not connected")
    
    def on_down_button(self):
        """Physical DOWN button pressed"""
        if self.carplay.is_phone_connected():
            controller = self.carplay.get_controller()
            controller.sendKey("down")
            print(f"   [OK] Sent DOWN command")
        else:
            print(f"   [ERROR] Phone not connected")
    
    def on_left_button(self):
        """Physical LEFT button pressed (or Previous Track)"""
        if self.carplay.is_phone_connected():
            self.carplay.send_previous_track()
            song = self.carplay.get_current_song()
            artist = self.carplay.get_current_artist()
            if song:
                print(f"   [OK] Previous Track: {song} - {artist}")
            else:
                print(f"   [OK] Sent Previous Track command")
        else:
            print(f"   [ERROR] Phone not connected")
    
    def on_right_button(self):
        """Physical RIGHT button pressed (or Next Track)"""
        if self.carplay.is_phone_connected():
            self.carplay.send_next_track()
            song = self.carplay.get_current_song()
            artist = self.carplay.get_current_artist()
            if song:
                print(f"   [OK] Next Track: {song} - {artist}")
            else:
                print(f"   [OK] Sent Next Track command")
        else:
            print(f"   [ERROR] Phone not connected")
    
    def on_ok_button(self):
        """Physical OK/ENTER button pressed"""
        if self.carplay.is_phone_connected():
            controller = self.carplay.get_controller()
            controller.sendKey("select")
            print(f"   [OK] Sent OK/SELECT command")
        else:
            print(f"   [ERROR] Phone not connected")
    
    def on_play_pause_button(self):
        """Physical PLAY/PAUSE button pressed"""
        if self.carplay.is_phone_connected():
            self.carplay.send_play_pause()
            song = self.carplay.get_current_song()
            if song:
                print(f"   [OK] Play/Pause: {song}")
            else:
                print(f"   [OK] Sent Play/Pause command")
        else:
            print(f"   [ERROR] Phone not connected")
    
    def on_volume_up_button(self):
        """Physical VOLUME UP button pressed"""
        controller = self.carplay.get_controller()
        # Get current volume and increase
        # In real app, track volume state
        self.carplay.set_volume(0.8)  # Example: set to 80%
    
    def on_volume_down_button(self):
        """Physical VOLUME DOWN button pressed"""
        self.carplay.set_volume(0.3)  # Example: set to 30%


class CarSystemApp(QMainWindow):
    """
    Main application simulating a car infotainment system
    with physical button integration
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Car System with Hardware Buttons")
        
        # Create central widget
        central = QWidget()
        layout = QVBoxLayout(central)
        
        # Info label
        info = QLabel(
            "Car Infotainment System\n\n"
            "This demo simulates physical hardware buttons.\n"
            "In real use, buttons would trigger CarPlay actions.\n\n"
            "Watch console for button press simulation..."
        )
        info.setStyleSheet("padding: 10px; background: #333; border-radius: 5px;")
        layout.addWidget(info)
        
        # CarPlay widget
        config = CarPlayConfig()
        config.video.width = 1280
        config.video.height = 720
        config.dongle.auto_connect = True
        
        self.carplay = CarPlayWidget(config=config)
        layout.addWidget(self.carplay)
        
        self.setCentralWidget(central)
        self.resize(1280, 800)
        
        # Setup hardware button simulator
        self.hardware = HardwareButtonSimulator(self.carplay)
        
        # Listen to CarPlay events
        self.carplay.phoneConnected.connect(self.on_phone_connected)
        self.carplay.phoneDisconnected.connect(self.on_phone_disconnected)
        self.carplay.currentSongChanged.connect(self.on_song_changed)
        
        # Monitor connection status every 5 seconds
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.check_status)
        self.status_timer.start(5000)
        
        # Start button simulation after 2 seconds
        QTimer.singleShot(2000, self.hardware.start_demo)
    
    def check_status(self):
        """Periodically check and display connection status"""
        if self.carplay.is_connected():
            status = self.carplay.get_status()
            if self.carplay.is_phone_connected():
                song = self.carplay.get_current_song()
                artist = self.carplay.get_current_artist()
                if song:
                    print(f"[STATUS] {status} | Now Playing: {song} - {artist}")
                else:
                    print(f"[STATUS] {status} | Ready")
            else:
                print(f"[STATUS] {status} | Waiting for phone...")
        else:
            print(f"[STATUS] Dongle not connected")
    
    def on_phone_connected(self):
        """Phone connected to CarPlay"""
        print("[PHONE] Phone connected to CarPlay!")
    
    def on_phone_disconnected(self):
        """Phone disconnected"""
        print("[PHONE] Phone disconnected")
    
    def on_song_changed(self, song: str):
        """Song changed"""
        if song:
            artist = self.carplay.get_current_artist()
            print(f"[MEDIA] Now playing: {song} - {artist}")


# === Example: Raspberry Pi GPIO Integration ===
"""
For real hardware buttons on Raspberry Pi:

import RPi.GPIO as GPIO

class RaspberryPiButtons:
    def __init__(self, carplay_widget):
        self.carplay = carplay_widget
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        
        # Define button pins
        BUTTON_HOME = 17
        BUTTON_BACK = 27
        BUTTON_UP = 22
        BUTTON_DOWN = 23
        BUTTON_LEFT = 24
        BUTTON_RIGHT = 25
        BUTTON_OK = 26
        
        # Setup as inputs with pull-up
        buttons = [BUTTON_HOME, BUTTON_BACK, BUTTON_UP, BUTTON_DOWN, 
                   BUTTON_LEFT, BUTTON_RIGHT, BUTTON_OK]
        for pin in buttons:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Add event detection
        GPIO.add_event_detect(BUTTON_HOME, GPIO.FALLING, 
                            callback=lambda x: self.carplay.send_home(), 
                            bouncetime=200)
        GPIO.add_event_detect(BUTTON_BACK, GPIO.FALLING, 
                            callback=lambda x: self.carplay.send_back(), 
                            bouncetime=200)
        GPIO.add_event_detect(BUTTON_OK, GPIO.FALLING, 
                            callback=lambda x: self.carplay.get_controller().sendKey("select"), 
                            bouncetime=200)
        # ... etc for other buttons
"""


# === Example: Serial Port / CAN Bus Integration ===
"""
For serial port commands from external controller:

import serial
from PySide6.QtCore import QThread, Signal

class SerialButtonReader(QThread):
    button_pressed = Signal(str)  # Emits button name
    
    def __init__(self):
        super().__init__()
        self.serial = serial.Serial('/dev/ttyUSB0', 9600)
        self.running = True
    
    def run(self):
        while self.running:
            if self.serial.in_waiting:
                command = self.serial.readline().decode().strip()
                self.button_pressed.emit(command)
    
    def stop(self):
        self.running = False
        self.serial.close()

# In your app:
class MyApp(QMainWindow):
    def __init__(self):
        self.carplay = CarPlayWidget()
        
        # Setup serial reader
        self.serial_reader = SerialButtonReader()
        self.serial_reader.button_pressed.connect(self.handle_serial_command)
        self.serial_reader.start()
    
    def handle_serial_command(self, command: str):
        # Map serial commands to CarPlay actions
        commands = {
            'HOME': self.carplay.send_home,
            'BACK': self.carplay.send_back,
            'UP': lambda: self.carplay.get_controller().sendKey('up'),
            'DOWN': lambda: self.carplay.get_controller().sendKey('down'),
            'PLAY': self.carplay.send_play_pause,
            'NEXT': self.carplay.send_next_track,
            'PREV': self.carplay.send_previous_track,
        }
        
        if command in commands:
            commands[command]()
"""


def main():
    app = QApplication(sys.argv)
    
    print("=" * 60)
    print("Hardware Buttons Integration Demo")
    print("=" * 60)
    print("\nThis demonstrates calling CarPlay actions from hardware.")
    print("Replace HardwareButtonSimulator with your actual hardware input.\n")
    
    window = CarSystemApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
