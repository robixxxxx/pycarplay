#!/usr/bin/env python3
"""
High-level CarPlay/AndroidAuto interface
Based on TypeScript carplay.ts implementation
"""
import time
import threading
from typing import Optional, Callable
from enum import IntEnum
from dataclasses import dataclass

from dongle_driver import DongleDriver, DongleConfig, DriverStateError
from messages import (
    Message, VideoData, AudioData, MediaData, Plugged, Unplugged,
    Command, AudioCommand, PhoneType,
    WifiMacAddress, BluetoothMacAddress, EthernetMacAddress
)
from sendable import SendCommand, SendAudio, SendTouch, TouchAction


class MessageType(IntEnum):
    """CarPlay message types for callbacks"""
    PLUGGED = 1
    UNPLUGGED = 2
    FAILURE = 3
    AUDIO = 4
    VIDEO = 5
    MEDIA = 6
    COMMAND = 7
    WIFI_MAC = 8
    BT_MAC = 9
    ETH_MAC = 10


@dataclass
class CarplayMessage:
    """CarPlay message wrapper"""
    msg_type: MessageType
    message: Optional[Message] = None


class CarplayNode:
    """High-level CarPlay/AndroidAuto interface"""
    
    USB_WAIT_PERIOD_MS = 3000
    PAIR_TIMEOUT_MS = 15000
    
    def __init__(self, config: DongleConfig):
        self.config = config
        self.dongle_driver = DongleDriver()
        
        # Timers and threads
        self._pair_timeout: Optional[threading.Timer] = None
        self._frame_interval: Optional[threading.Timer] = None
        self._frame_interval_active = False
        
        # Callback
        self.onmessage: Optional[Callable[[CarplayMessage], None]] = None
        self._microphone_callback: Optional[Callable[[str, AudioCommand], None]] = None
        
        # Setup driver callbacks
        self.dongle_driver.on_message(self._on_driver_message)
        self.dongle_driver.on_failure(self._on_driver_failure)
    
    def _on_driver_message(self, message: Message):
        """Handle messages from dongle driver"""
        
        if isinstance(message, Plugged):
            self._clear_pair_timeout()
            self._clear_frame_interval()
            
            # Setup frame interval for CarPlay if configured
            phone_config = self.config.phone_config.get(message.phone_type)
            if phone_config and phone_config.frame_interval:
                self._start_frame_interval(phone_config.frame_interval)
            
            if self.onmessage:
                self.onmessage(CarplayMessage(MessageType.PLUGGED, message))
        
        elif isinstance(message, Unplugged):
            self._clear_frame_interval()
            if self.onmessage:
                self.onmessage(CarplayMessage(MessageType.UNPLUGGED, message))
        
        elif isinstance(message, VideoData):
            self._clear_pair_timeout()
            if self.onmessage:
                self.onmessage(CarplayMessage(MessageType.VIDEO, message))
        
        elif isinstance(message, AudioData):
            self._clear_pair_timeout()
            
            # Handle audio commands (Siri, phone calls)
            if message.command is not None:
                self._handle_audio_command(message.command)
            
            if self.onmessage:
                self.onmessage(CarplayMessage(MessageType.AUDIO, message))
        
        elif isinstance(message, MediaData):
            self._clear_pair_timeout()
            if self.onmessage:
                self.onmessage(CarplayMessage(MessageType.MEDIA, message))
        
        elif isinstance(message, Command):
            if self.onmessage:
                self.onmessage(CarplayMessage(MessageType.COMMAND, message))
        
        elif isinstance(message, WifiMacAddress):
            if self.onmessage:
                self.onmessage(CarplayMessage(MessageType.WIFI_MAC, message))
        
        elif isinstance(message, BluetoothMacAddress):
            if self.onmessage:
                self.onmessage(CarplayMessage(MessageType.BT_MAC, message))
        
        elif isinstance(message, EthernetMacAddress):
            if self.onmessage:
                self.onmessage(CarplayMessage(MessageType.ETH_MAC, message))
    
    def _on_driver_failure(self):
        """Handle driver failure"""
        if self.onmessage:
            self.onmessage(CarplayMessage(MessageType.FAILURE))
    
    def _handle_audio_command(self, command: AudioCommand):
        """Handle audio commands (Siri, phone calls)"""
        if command in (AudioCommand.AudioSiriStart, AudioCommand.AudioPhonecallStart):
            print(f"🎤 Audio started: {command.name}")
            # Call microphone start callback
            if self._microphone_callback:
                self._microphone_callback('start', command)
            else:
                print(f"🎤 WARNING: No microphone callback set!")
        elif command in (AudioCommand.AudioSiriStop, AudioCommand.AudioPhonecallStop):
            print(f"🎤 Audio stopped: {command.name}")
            # Call microphone stop callback
            if self._microphone_callback:
                self._microphone_callback('stop', command)
            else:
                print(f"🎤 WARNING: No microphone callback set!")
    
    def _start_frame_interval(self, interval_ms: int):
        """Start sending frame requests periodically"""
        print(f"Starting frame interval: {interval_ms}ms")
        self._frame_interval_active = True
        
        def send_frame():
            if self._frame_interval_active:
                self.dongle_driver.send(SendCommand('frame'))
                self._frame_interval = threading.Timer(
                    interval_ms / 1000.0,
                    send_frame
                )
                self._frame_interval.daemon = True
                self._frame_interval.start()
        
        send_frame()
    
    def _clear_pair_timeout(self):
        """Clear pairing timeout"""
        if self._pair_timeout:
            self._pair_timeout.cancel()
            self._pair_timeout = None
    
    def _clear_frame_interval(self):
        """Clear frame interval"""
        self._frame_interval_active = False
        if self._frame_interval:
            self._frame_interval.cancel()
            self._frame_interval = None
    
    def find_device(self):
        """Find USB device (blocking until found)"""
        print("Looking for USB device...")
        device = None
        
        while device is None:
            device = self.dongle_driver.find_device()
            if device is None:
                print("No device found, retrying in 3s...")
                time.sleep(self.USB_WAIT_PERIOD_MS / 1000.0)
        
        print(f"Found device: {device}")
        return device
    
    def start(self):
        """Start CarPlay/AndroidAuto session"""
        try:
            # Note: USB reset is done in TypeScript but can cause issues in PyUSB
            # Uncomment if needed:
            # print("Resetting device...")
            # device = self.find_device()
            # device.reset()
            # time.sleep(self.USB_WAIT_PERIOD_MS / 1000.0)
            
            print("Initializing dongle driver...")
            self.dongle_driver.initialise()
            
            print("Starting communication...")
            self.dongle_driver.start(self.config)
            
            # Setup pair timeout (send wifiPair if no device connects)
            print("Setting up pair timeout...")
            self._pair_timeout = threading.Timer(
                self.PAIR_TIMEOUT_MS / 1000.0,
                lambda: self.dongle_driver.send(SendCommand('wifiPair'))
            )
            self._pair_timeout.daemon = True
            self._pair_timeout.start()
            
            print("CarPlay started successfully")
            return True
            
        except Exception as err:
            print(f"Failed to start CarPlay: {err}")
            import traceback
            traceback.print_exc()
            
            # Retry after 2 seconds
            print("Retrying in 2s...")
            time.sleep(2)
            return self.start()
    
    def stop(self):
        """Stop CarPlay/AndroidAuto session"""
        try:
            print("Stopping CarPlay...")
            self._clear_pair_timeout()
            self._clear_frame_interval()
            self.dongle_driver.close()
            print("CarPlay stopped")
        except Exception as err:
            print(f"Error stopping CarPlay: {err}")
    
    def send_key(self, action: str):
        """Send key command (home, back, play, etc.)"""
        self.dongle_driver.send(SendCommand(action))
    
    def send_touch(self, x: float, y: float, action: TouchAction):
        """Send touch event"""
        self.dongle_driver.send(SendTouch(x, y, action))
    
    def send_audio(self, audio_data: bytes):
        """Send audio data (microphone)"""
        self.dongle_driver.send(SendAudio(audio_data))


if __name__ == "__main__":
    """Test CarPlay node"""
    from dongle_driver import DongleConfig, HandDriveType
    
    config = DongleConfig(
        width=1280,
        height=720,
        fps=30,
        dpi=160,
        box_name="pyCarPlay",
        hand=HandDriveType.LHD,
        wifi_type="5ghz",
        mic_type="os"
    )
    
    carplay = CarplayNode(config)
    
    def on_message(msg: CarplayMessage):
        print(f"Message: {msg.msg_type.name}")
        
        if msg.msg_type == MessageType.VIDEO and msg.message:
            video = msg.message
            print(f"  Video: {video.width}x{video.height}, {len(video.data)} bytes")
        elif msg.msg_type == MessageType.AUDIO and msg.message:
            audio = msg.message
            if audio.data:
                print(f"  Audio: {len(audio.data)} samples")
        elif msg.msg_type == MessageType.PLUGGED and msg.message:
            plugged = msg.message
            print(f"  Phone: {plugged.phone_type.name}")
        elif msg.msg_type == MessageType.MEDIA and msg.message:
            media = msg.message
            print(f"  Media: {media.payload}")
    
    carplay.onmessage = on_message
    
    try:
        carplay.start()
        
        print("\nCarPlay running. Press Ctrl+C to stop.")
        print("Available commands:")
        print("  - Connect iPhone/Android to dongle")
        print("  - Video/audio will be logged here")
        
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\nStopping...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        carplay.stop()
