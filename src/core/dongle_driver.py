#!/usr/bin/env python3
"""
USB Dongle Driver for CarPlay/AndroidAuto
Based on TypeScript implementation
"""
import usb.core
import usb.util
import threading
import time
from enum import IntEnum
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from ..protocol.messages import MessageHeader, HeaderBuildError, PhoneType
from ..protocol.sendable import (
    SendableMessage, SendNumber, SendBoolean, SendString,
    SendOpen, SendBoxSettings, SendCommand, HeartBeat, FileAddress
)


class HandDriveType(IntEnum):
    LHD = 0
    RHD = 1


@dataclass
class PhoneTypeConfig:
    frame_interval: Optional[int] = None


@dataclass
class DongleConfig:
    width: int = 800
    height: int = 640
    fps: int = 30
    dpi: int = 160
    format: int = 5
    ibox_version: int = 2
    phone_work_mode: int = 2
    packet_max: int = 49152
    box_name: str = "pyCarPlay"
    night_mode: bool = False
    hand: HandDriveType = HandDriveType.LHD
    media_delay: int = 300
    audio_transfer_mode: bool = False
    wifi_type: str = "5ghz"  # "2.4ghz" or "5ghz"
    mic_type: str = "os"  # "box" or "os"
    android_work_mode: Optional[bool] = None
    phone_config: Dict[PhoneType, PhoneTypeConfig] = None

    def __post_init__(self):
        if self.phone_config is None:
            self.phone_config = {
                PhoneType.CarPlay: PhoneTypeConfig(frame_interval=5000),
                PhoneType.AndroidAuto: PhoneTypeConfig(frame_interval=None),
            }


class DriverStateError(Exception):
    """Driver state error"""
    pass


class DongleDriver:
    """USB Dongle Driver for CarPlay/AndroidAuto"""
    
    KNOWN_DEVICES = [
        {'vendor_id': 0x1314, 'product_id': 0x1520},
        {'vendor_id': 0x1314, 'product_id': 0x1521},
    ]
    
    CONFIG_NUMBER = 1
    MAX_ERROR_COUNT = 20  # Increased to allow USB error recovery
    
    def __init__(self):
        self.device: Optional[usb.core.Device] = None
        self.in_ep: Optional[usb.core.Endpoint] = None
        self.out_ep: Optional[usb.core.Endpoint] = None
        self.config: Optional[DongleConfig] = None
        self.error_count = 0
        self._running = False
        self._read_thread: Optional[threading.Thread] = None
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._message_callbacks: list[Callable] = []
        self._failure_callbacks: list[Callable] = []
    
    def on_message(self, callback: Callable):
        """Register message callback"""
        self._message_callbacks.append(callback)
    
    def on_failure(self, callback: Callable):
        """Register failure callback"""
        self._failure_callbacks.append(callback)
    
    def find_device(self) -> Optional[usb.core.Device]:
        """Find known USB device"""
        for device_info in self.KNOWN_DEVICES:
            device = usb.core.find(
                idVendor=device_info['vendor_id'],
                idProduct=device_info['product_id']
            )
            if device:
                return device
        return None
    
    def initialise(self, device: Optional[usb.core.Device] = None):
        """Initialize USB device"""
        if self.device:
            print("Device already initialized")
            return
        
        if device is None:
            device = self.find_device()
        
        if device is None:
            raise DriverStateError("No compatible device found")
        
        try:
            self.device = device
            print(f"Initializing device: {device}")
            
            # Detach kernel driver if necessary
            if self.device.is_kernel_driver_active(0):
                print("Detaching kernel driver")
                self.device.detach_kernel_driver(0)
            
            # Set configuration
            self.device.set_configuration(self.CONFIG_NUMBER)
            cfg = self.device.get_active_configuration()
            
            # Get interface and endpoints
            intf = cfg[(0, 0)]
            
            # Find IN and OUT endpoints
            self.out_ep = usb.util.find_descriptor(
                intf,
                custom_match=lambda e: \
                    usb.util.endpoint_direction(e.bEndpointAddress) == \
                    usb.util.ENDPOINT_OUT
            )
            
            self.in_ep = usb.util.find_descriptor(
                intf,
                custom_match=lambda e: \
                    usb.util.endpoint_direction(e.bEndpointAddress) == \
                    usb.util.ENDPOINT_IN
            )
            
            if self.in_ep is None:
                raise DriverStateError("No IN endpoint found")
            
            if self.out_ep is None:
                raise DriverStateError("No OUT endpoint found")
            
            print(f"IN Endpoint: {self.in_ep.bEndpointAddress:#x}")
            print(f"OUT Endpoint: {self.out_ep.bEndpointAddress:#x}")
            
        except Exception as err:
            self.close()
            raise err
    
    def send(self, message: SendableMessage) -> bool:
        """Send message to device"""
        if not self.device:
            return False
        
        try:
            payload = message.serialise()
            bytes_written = self.out_ep.write(payload)
            return bytes_written == len(payload)
        except usb.core.USBError as err:
            error_str = str(err)
            # Check for device disconnection
            if "No such device" in error_str or "Entity not found" in error_str or err.errno == 19:
                print(f"❌ USB device disconnected during send!")
                self._running = False
                for callback in self._failure_callbacks:
                    callback()
                return False
            print(f"Failure sending message to dongle: {err}")
            return False
        except Exception as err:
            print(f"Failure sending message to dongle: {err}")
            return False
    
    def _read_loop(self):
        """Read loop for incoming messages"""
        print("Starting read loop")
        while self._running and self.device:
            if self.error_count >= self.MAX_ERROR_COUNT:
                print("Max error count reached, closing")
                self._running = False  # Set flag first to stop heartbeat
                for callback in self._failure_callbacks:
                    callback()
                return
            
            try:
                # Read header (16 bytes)
                header_data = self.in_ep.read(MessageHeader.DATA_LENGTH, timeout=1000)
                
                # Try to parse header
                try:
                    header = MessageHeader.from_buffer(bytes(header_data))
                except ValueError as e:
                    # Unknown message type - skip this message
                    print(f"Skipping message: {e}")
                    continue
                
                # Read extra data if needed
                extra_data = None
                if header.length > 0:
                    # Read in chunks to avoid overflow
                    # USB bulk endpoint max packet size is typically 512 bytes
                    # but we may need to read larger payloads (video frames can be 50KB+)
                    chunks = []
                    remaining = header.length
                    while remaining > 0:
                        chunk_size = min(remaining, 16384)  # Read max 16KB at a time
                        chunk = self.in_ep.read(chunk_size, timeout=2000)
                        chunks.append(bytes(chunk))
                        remaining -= len(chunk)
                    extra_data = b''.join(chunks)
                
                # Convert to message object
                message = header.to_message(extra_data)
                
                # Reset error count on successful read
                if message:
                    self.error_count = 0
                
                # Emit message
                if message:
                    for callback in self._message_callbacks:
                        callback(message)
                
            except usb.core.USBTimeoutError:
                # Timeout is normal, continue
                continue
            except usb.core.USBError as error:
                # Check for device disconnection errors
                error_str = str(error)
                if "No such device" in error_str or "Entity not found" in error_str or error.errno == 19:
                    print("❌ USB device disconnected!")
                    self._running = False
                    for callback in self._failure_callbacks:
                        callback()
                    return
                # Other USB errors - log and continue
                print(f"USB error in read loop: {error}")
                self.error_count += 1
            except HeaderBuildError as error:
                print(f"Error parsing header: {error}")
                self.error_count += 1
            except OSError as error:
                # Handle USB errors (Overflow, Pipe error, etc.)
                error_str = str(error)
                print(f"USB error in read loop: {error}")
                
                if "Overflow" in error_str:
                    # USB buffer overflow - need to flush the endpoint
                    print("USB Overflow detected - flushing endpoint buffer...")
                    try:
                        # Try to drain the endpoint buffer
                        while True:
                            try:
                                self.in_ep.read(self.in_ep.wMaxPacketSize, timeout=100)
                            except usb.core.USBTimeoutError:
                                # Timeout means buffer is empty
                                break
                            except:
                                break
                        # Clear halt condition
                        usb.util.clear_halt(self.device, self.in_ep)
                        print("Endpoint flushed and cleared")
                        # Don't increment error count for overflow - it's recoverable
                        time.sleep(0.2)
                        continue
                    except Exception as e:
                        print(f"Failed to clear endpoint: {e}")
                
                if "Pipe error" in error_str:
                    # Pipe error - try to clear halt
                    print("Pipe error - attempting endpoint recovery...")
                    try:
                        usb.util.clear_halt(self.device, self.in_ep)
                        time.sleep(0.1)
                    except:
                        pass
                
                self.error_count += 1
            except Exception as error:
                error_str = str(error)
                # Don't spam common non-critical errors
                if "BLUETOOTH_ADDRESS" not in error_str and "BLUETOOTH" not in error_str:
                    print(f"Error in read loop: {error}")
                self.error_count += 1
        
        print("Read loop stopped")
    
    def _heartbeat_loop(self):
        """Heartbeat loop"""
        print("Starting heartbeat loop")
        while self._running:
            self.send(HeartBeat())
            time.sleep(2)
        print("Heartbeat loop stopped")
    
    def update_video_settings(self, width: int, height: int, dpi: int):
        """Update video resolution and DPI
        
        Args:
            width: Video width in pixels
            height: Video height in pixels
            dpi: DPI value
        """
        if not self.config:
            raise DriverStateError("No config - call start first")
        
        # Update config
        self.config.width = width
        self.config.height = height
        self.config.dpi = dpi
        
        # Send updates to dongle
        self.send(SendNumber(dpi, FileAddress.DPI))
        self.send(SendBoxSettings(self.config))
        
        print(f"📤 Video settings sent to dongle: {width}x{height} @ {dpi} DPI")
    
    def start(self, config: DongleConfig):
        """Start communication with device"""
        if not self.device:
            raise DriverStateError("No device set - call initialise first")
        
        # Store config for later updates
        self.config = config
        
        self.error_count = 0
        self._running = True
        
        # Send initialization messages
        print("Sending initialization messages")
        init_messages = [
            SendNumber(config.dpi, FileAddress.DPI),
            SendOpen(config),
            SendBoolean(config.night_mode, FileAddress.NIGHT_MODE),
            SendNumber(config.hand, FileAddress.HAND_DRIVE_MODE),
            SendBoolean(True, FileAddress.CHARGE_MODE),
            SendString(config.box_name, FileAddress.BOX_NAME),
            SendBoxSettings(config),
            SendCommand('wifiEnable'),
            SendCommand('wifi5g' if config.wifi_type == '5ghz' else 'wifi24g'),
            SendCommand('boxMic' if config.mic_type == 'box' else 'mic'),
            SendCommand('audioTransferOn' if config.audio_transfer_mode else 'audioTransferOff'),
        ]
        
        if config.android_work_mode is not None:
            init_messages.append(
                SendBoolean(config.android_work_mode, FileAddress.ANDROID_WORK_MODE)
            )
        
        for msg in init_messages:
            self.send(msg)
        
        # Delay for wifi connect
        time.sleep(1)
        self.send(SendCommand('wifiConnect'))
        
        # Start read thread
        self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._read_thread.start()
        
        # Start heartbeat thread
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        
        print("Driver started")
    
    def close(self):
        """Close device connection"""
        print("Closing driver")
        self._running = False
        
        # Don't try to join ourselves if we're calling from read/heartbeat thread
        current_thread = threading.current_thread()
        
        if self._read_thread and self._read_thread != current_thread:
            self._read_thread.join(timeout=2)
        
        if self._heartbeat_thread and self._heartbeat_thread != current_thread:
            self._heartbeat_thread.join(timeout=2)
        
        if self.device:
            try:
                usb.util.dispose_resources(self.device)
            except:
                pass
            self.device = None
        
        self.in_ep = None
        self.out_ep = None
        print("Driver closed")


if __name__ == "__main__":
    # Test code
    driver = DongleDriver()
    
    def on_message(message):
        """Handle received message"""
        from ..protocol.messages import VideoData, AudioData, Plugged
        
        if isinstance(message, VideoData):
            print(f"Video: {message.width}x{message.height}, {len(message.data)} bytes")
        elif isinstance(message, AudioData):
            if message.data:
                print(f"Audio: {len(message.data)} samples")
        elif isinstance(message, Plugged):
            print(f"Phone plugged: {message.phone_type.name}")
        else:
            msg_type = message.header.type.name if hasattr(message.header, 'type') else 'Unknown'
            print(f"Message: {msg_type}")
    
    def on_failure():
        print("Driver failed!")
    
    driver.on_message(on_message)
    driver.on_failure(on_failure)
    
    try:
        driver.initialise()
        config = DongleConfig()
        driver.start(config)
        
        # Keep running
        print("Driver running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()
