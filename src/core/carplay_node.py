#!/usr/bin/env python3
"""
CarPlay Node - High-level CarPlay/AndroidAuto Interface

Provides a clean API for interacting with CarPlay dongles.
Based on TypeScript carplay.ts implementation.

Features:
- Message routing and callbacks
- Automatic pairing and frame requests
- Touch and key command sending
- Audio input (microphone) support
"""
import time
import threading
from typing import Optional, Callable
from enum import IntEnum
from dataclasses import dataclass

from .dongle_driver import DongleDriver, DongleConfig, DriverStateError
from ..protocol.messages import (
    Message, VideoData, AudioData, MediaData, Plugged, Unplugged,
    Command, AudioCommand, PhoneType,
    WifiMacAddress, BluetoothMacAddress, EthernetMacAddress
)
from ..protocol.sendable import SendCommand, SendAudio, SendTouch, TouchAction


class MessageType(IntEnum):
    """Message types for CarPlay callbacks"""
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
    """Wrapper for CarPlay messages with type information"""
    msg_type: MessageType
    message: Optional[Message] = None


class CarplayNode:
    """High-level CarPlay/AndroidAuto interface
    
    Manages dongle connection, message routing, and user input.
    """
    
    # Timing constants
    USB_WAIT_PERIOD_MS = 3000
    PAIR_TIMEOUT_MS = 15000
    
    def __init__(self, config: DongleConfig):
        self.config = config
        self.dongle_driver = DongleDriver()
        
        # === Timers ===
        self._pair_timeout: Optional[threading.Timer] = None
        self._frame_interval: Optional[threading.Timer] = None
        self._frame_interval_active = False
        
        # === Callbacks ===
        self.onmessage: Optional[Callable[[CarplayMessage], None]] = None
        self._microphone_callback: Optional[Callable[[str, AudioCommand], None]] = None
        
        # === Setup ===
        self.dongle_driver.on_message(self._on_driver_message)
        self.dongle_driver.on_failure(self._on_driver_failure)
    
    # === Message Handlers ===
    
    def _on_driver_message(self, message: Message):
        """Route messages from dongle driver to appropriate handlers"""
        
        if isinstance(message, Plugged):
            self._handle_plugged(message)
        elif isinstance(message, Unplugged):
            self._handle_unplugged(message)
        elif isinstance(message, VideoData):
            self._handle_video(message)
        elif isinstance(message, AudioData):
            self._handle_audio(message)
        elif isinstance(message, MediaData):
            self._handle_media(message)
        elif isinstance(message, Command):
            self._handle_command(message)
        elif isinstance(message, WifiMacAddress):
            self._notify(MessageType.WIFI_MAC, message)
        elif isinstance(message, BluetoothMacAddress):
            self._notify(MessageType.BT_MAC, message)
        elif isinstance(message, EthernetMacAddress):
            self._notify(MessageType.ETH_MAC, message)
    
    def _notify(self, msg_type: MessageType, message: Message = None):
        """Send notification to callback"""
        if self.onmessage:
            self.onmessage(CarplayMessage(msg_type, message))
    
    def _handle_plugged(self, message: Plugged):
        """Handle phone plugged event"""
        self._clear_pair_timeout()
        self._clear_frame_interval()
        
        # Setup frame interval for CarPlay if configured
        phone_config = self.config.phone_config.get(message.phone_type)
        if phone_config and phone_config.frame_interval:
            self._start_frame_interval(phone_config.frame_interval)
        
        self._notify(MessageType.PLUGGED, message)
    
    def _handle_unplugged(self, message: Unplugged):
        """Handle phone unplugged event"""
        self._clear_frame_interval()
        self._notify(MessageType.UNPLUGGED, message)
    
    def _handle_video(self, message: VideoData):
        """Handle video data"""
        self._clear_pair_timeout()
        self._notify(MessageType.VIDEO, message)
    
    def _handle_audio(self, message: AudioData):
        """Handle audio data and commands"""
        self._clear_pair_timeout()
        
        # Handle audio commands (Siri, phone calls)
        if message.command is not None:
            self._handle_audio_command(message.command)
        
        self._notify(MessageType.AUDIO, message)
    
    def _handle_media(self, message: MediaData):
        """Handle media metadata"""
        self._clear_pair_timeout()
        self._notify(MessageType.MEDIA, message)
    
    def _handle_command(self, message: Command):
        """Handle system commands"""
        self._notify(MessageType.COMMAND, message)
    
    def _handle_audio_command(self, command: AudioCommand):
        """Handle audio commands and trigger microphone callback"""
        if command in (AudioCommand.AudioSiriStart, AudioCommand.AudioPhonecallStart):
            print(f"🎤 Audio started: {command.name}")
            if self._microphone_callback:
                self._microphone_callback('start', command)
            else:
                print(f"⚠️  No microphone callback set")
        elif command in (AudioCommand.AudioSiriStop, AudioCommand.AudioPhonecallStop):
            print(f"🎤 Audio stopped: {command.name}")
            if self._microphone_callback:
                self._microphone_callback('stop', command)
            else:
                print(f"⚠️  No microphone callback set")
    
    def _on_driver_failure(self):
        """Handle driver failure"""
        self._notify(MessageType.FAILURE)
    
    # === Timer Management ===
    
    def _start_frame_interval(self, interval_ms: int):
        """Start sending frame requests periodically"""
        print(f"⏱️  Frame interval: {interval_ms}ms")
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
        """Cancel pairing timeout timer"""
        if self._pair_timeout:
            self._pair_timeout.cancel()
            self._pair_timeout = None
    
    def _clear_frame_interval(self):
        """Stop frame request timer"""
        self._frame_interval_active = False
        if self._frame_interval:
            self._frame_interval.cancel()
            self._frame_interval = None
    
    # === Public API ===
    
    def find_device(self):
        """Find USB device (blocks until found)
        
        Returns:
            USB device object
        """
        print("🔍 Looking for USB device...")
        device = None
        
        while device is None:
            device = self.dongle_driver.find_device()
            if device is None:
                print("⏳ No device found, retrying in 3s...")
                time.sleep(self.USB_WAIT_PERIOD_MS / 1000.0)
        
        print(f"✅ Found device: {device}")
        return device
    
    def start(self):
        """Start CarPlay/AndroidAuto session
        
        Initializes dongle, starts communication, and sets up pairing.
        Will retry automatically on failure.
        
        Returns:
            True on success
        """
        try:
            print("🚀 Initializing dongle driver...")
            self.dongle_driver.initialise()
            
            print("📡 Starting communication...")
            self.dongle_driver.start(self.config)
            
            # Setup pair timeout (send wifiPair if no device connects)
            print(f"⏱️  Setting up pair timeout ({self.PAIR_TIMEOUT_MS}ms)...")
            self._pair_timeout = threading.Timer(
                self.PAIR_TIMEOUT_MS / 1000.0,
                lambda: self.dongle_driver.send(SendCommand('wifiPair'))
            )
            self._pair_timeout.daemon = True
            self._pair_timeout.start()
            
            print("✅ CarPlay started successfully")
            return True
            
        except Exception as err:
            print(f"❌ Failed to start CarPlay: {err}")
            import traceback
            traceback.print_exc()
            
            # Notify failure
            self._notify(MessageType.FAILURE)
            return False
    
    def stop(self):
        """Stop CarPlay/AndroidAuto session
        
        Cleans up timers and closes dongle connection.
        """
        try:
            print("🛑 Stopping CarPlay...")
            self._clear_pair_timeout()
            self._clear_frame_interval()
            self.dongle_driver.close()
            print("✅ CarPlay stopped")
        except Exception as err:
            print(f"❌ Error stopping CarPlay: {err}")
    
    def send_key(self, action: str):
        """Send key command to CarPlay
        
        Args:
            action: Command name (home, back, play, pause, etc.)
        """
        self.dongle_driver.send(SendCommand(action))
    
    def send_touch(self, x: float, y: float, action: TouchAction):
        """Send touch event to CarPlay
        
        Args:
            x: Normalized X coordinate (0.0-1.0)
            y: Normalized Y coordinate (0.0-1.0)
            action: Touch action (Down, Move, Up)
        """
        self.dongle_driver.send(SendTouch(x, y, action))
    
    def send_audio(self, audio_data: bytes):
        """Send microphone audio data to CarPlay
        
        Args:
            audio_data: PCM audio bytes (16-bit, mono, 16kHz)
        """
        self.dongle_driver.send(SendAudio(audio_data))


# === Test / Demo Code ===

if __name__ == "__main__":
    """Test CarPlay node with basic message logging"""
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
