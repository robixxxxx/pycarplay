#!/usr/bin/env python3
"""
Message classes for USB Dongle communication
Based on TypeScript implementation
"""
import struct
import json
from enum import IntEnum
from typing import Optional, Union, Dict, Any
from dataclasses import dataclass


class AudioCommand(IntEnum):
    AudioOutputStart = 1
    AudioOutputStop = 2
    AudioInputConfig = 3
    AudioPhonecallStart = 4
    AudioPhonecallStop = 5
    AudioNaviStart = 6
    AudioNaviStop = 7
    AudioSiriStart = 8
    AudioSiriStop = 9
    AudioMediaStart = 10
    AudioMediaStop = 11
    AudioAlertStart = 12
    AudioAlertStop = 13
    Unknown_14 = 14
    Unknown_15 = 15
    Unknown_16 = 16  # Seen in logs
    Unknown_17 = 17


class PhoneType(IntEnum):
    AndroidMirror = 1
    CarPlay = 3
    iPhoneMirror = 4
    AndroidAuto = 5
    HiCar = 6


class MediaType(IntEnum):
    Data = 1
    AlbumCover = 3


@dataclass
class AudioFormat:
    frequency: int  # 48000, 44100, 24000, 16000, 8000
    channel: int    # 1 or 2
    bit_depth: int
    format: str
    mime_type: str


DECODE_TYPE_MAP: Dict[int, AudioFormat] = {
    1: AudioFormat(44100, 2, 16, "S16LE", "audio/L16; rate=44100; channels=2"),
    2: AudioFormat(44100, 2, 16, "S16LE", "audio/L16; rate=44100; channels=2"),
    3: AudioFormat(8000, 1, 16, "S16LE", "audio/L16; rate=8000; channels=1"),
    4: AudioFormat(48000, 2, 16, "S16LE", "audio/L16; rate=48000; channels=2"),
    5: AudioFormat(16000, 1, 16, "S16LE", "audio/L16; rate=16000; channels=1"),
    6: AudioFormat(24000, 1, 16, "S16LE", "audio/L16; rate=24000; channels=1"),
    7: AudioFormat(16000, 2, 16, "S16LE", "audio/L16; rate=16000; channels=2"),
}


class MessageType(IntEnum):
    """Message type enumeration"""
    Open = 0x01
    Plugged = 0x02
    Phase = 0x03
    Unplugged = 0x04
    Touch = 0x05
    VideoData = 0x06
    AudioData = 0x07
    Command = 0x08
    LogoType = 0x09
    DisconnectPhone = 0x0f
    CloseDongle = 0x15
    BluetoothAddress = 0x0a
    BluetoothPIN = 0x0c
    BluetoothDeviceName = 0x0d
    WifiDeviceName = 0x0e
    BluetoothPairedList = 0x12
    ManufacturerInfo = 0x14
    MultiTouch = 0x17
    HiCarLink = 0x18
    BoxSettings = 0x19
    # Unknown types - firmware specific extensions (possibly MAC addresses or config)
    WifiMacAddress = 0x23  # Appears to be WiFi MAC address (B4:85:E1:A4:14:58 format)
    BluetoothMacAddress = 0x24  # Likely Bluetooth MAC address
    Unknown_0x25 = 0x25  # Unknown - possibly USB/other network interface
    EthernetMacAddress = 0x26  # Likely Ethernet MAC address
    MediaData = 0x2a
    SendFile = 0x99
    HeartBeat = 0xaa
    SoftwareVersion = 0xcc


class HeaderBuildError(Exception):
    """Header build error"""
    pass


class MessageHeader:
    """Message header structure"""
    DATA_LENGTH = 16  # Size of header in bytes
    MAGIC = 0x55aa55aa
    
    def __init__(self, length: int, msg_type: MessageType):
        self.length = length
        self.type = msg_type
    
    @classmethod
    def from_buffer(cls, buffer: bytes) -> 'MessageHeader':
        """Parse header from buffer"""
        if len(buffer) != cls.DATA_LENGTH:
            raise HeaderBuildError(f"Invalid buffer size - Expecting 16, got {len(buffer)}")
        
        # Format: [magic:4bytes][length:4bytes][type:4bytes][typeCheck:4bytes]
        magic = struct.unpack('<I', buffer[0:4])[0]
        if magic != cls.MAGIC:
            raise HeaderBuildError(f"Invalid magic number, received {magic:#x}")
        
        length = struct.unpack('<I', buffer[4:8])[0]
        msg_type_raw = struct.unpack('<I', buffer[8:12])[0]
        type_check = struct.unpack('<I', buffer[12:16])[0]
        
        expected_check = ((msg_type_raw ^ -1) & 0xffffffff)
        if type_check != expected_check:
            raise HeaderBuildError(f"Invalid type check, received {type_check:#x}, expected {expected_check:#x}")
        
        # Try to create MessageType enum, handle unknown types gracefully
        try:
            msg_type = MessageType(msg_type_raw)
        except ValueError:
            # Unknown message type - create a placeholder
            print(f"Warning: Unknown message type {msg_type_raw:#x}, skipping")
            raise ValueError(f"Unknown message type: {msg_type_raw:#x}")
        
        return cls(length, msg_type)
    
    @staticmethod
    def as_buffer(message_type: MessageType, byte_length: int) -> bytes:
        """Create header buffer"""
        magic = struct.pack('<I', MessageHeader.MAGIC)
        data_len = struct.pack('<I', byte_length)
        msg_type = struct.pack('<I', message_type)
        type_check = struct.pack('<I', ((message_type ^ -1) & 0xffffffff))
        return magic + data_len + msg_type + type_check
    
    def to_message(self, data: Optional[bytes] = None):
        """Convert header and data to appropriate Message object"""
        return create_message(self, data)


class Message:
    """Base message class"""
    
    def __init__(self, header: MessageHeader):
        self.header = header


class Command(Message):
    """Command message"""
    
    def __init__(self, header: MessageHeader, data: bytes):
        super().__init__(header)
        self.value = struct.unpack('<I', data[0:4])[0]


class ManufacturerInfo(Message):
    """Manufacturer info message"""
    
    def __init__(self, header: MessageHeader, data: bytes):
        super().__init__(header)
        self.a = struct.unpack('<I', data[0:4])[0]
        self.b = struct.unpack('<I', data[4:8])[0]


class SoftwareVersion(Message):
    """Software version message"""
    
    def __init__(self, header: MessageHeader, data: bytes):
        super().__init__(header)
        self.version = data.decode('ascii', errors='ignore').rstrip('\x00')


class BluetoothAddress(Message):
    """Bluetooth address message"""
    
    def __init__(self, header: MessageHeader, data: bytes):
        super().__init__(header)
        try:
            self.address = data.decode('ascii', errors='ignore').rstrip('\x00') if data else ""
        except Exception:
            self.address = ""


class BluetoothPIN(Message):
    """Bluetooth PIN message"""
    
    def __init__(self, header: MessageHeader, data: bytes):
        super().__init__(header)
        self.pin = data.decode('ascii', errors='ignore').rstrip('\x00')


class BluetoothDeviceName(Message):
    """Bluetooth device name message"""
    
    def __init__(self, header: MessageHeader, data: bytes):
        super().__init__(header)
        self.name = data.decode('ascii', errors='ignore').rstrip('\x00')


class WifiDeviceName(Message):
    """WiFi device name message"""
    
    def __init__(self, header: MessageHeader, data: bytes):
        super().__init__(header)
        self.name = data.decode('ascii', errors='ignore').rstrip('\x00')


class HiCarLink(Message):
    """HiCar link message"""
    
    def __init__(self, header: MessageHeader, data: bytes):
        super().__init__(header)
        self.link = data.decode('ascii', errors='ignore').rstrip('\x00')


class BluetoothPairedList(Message):
    """Bluetooth paired list message"""
    
    def __init__(self, header: MessageHeader, data: bytes):
        super().__init__(header)
        self.data = data.decode('ascii', errors='ignore').rstrip('\x00')


class WifiMacAddress(Message):
    """WiFi MAC address message"""
    
    def __init__(self, header: MessageHeader, data: bytes):
        super().__init__(header)
        self.mac = data.decode('ascii', errors='ignore').rstrip('\x00')


class BluetoothMacAddress(Message):
    """Bluetooth MAC address message"""
    
    def __init__(self, header: MessageHeader, data: bytes):
        super().__init__(header)
        self.mac = data.decode('ascii', errors='ignore').rstrip('\x00')


class EthernetMacAddress(Message):
    """Ethernet MAC address message"""
    
    def __init__(self, header: MessageHeader, data: bytes):
        super().__init__(header)
        self.mac = data.decode('ascii', errors='ignore').rstrip('\x00')


class Plugged(Message):
    """Phone plugged message"""
    
    def __init__(self, header: MessageHeader, data: bytes):
        super().__init__(header)
        wifi_avail = len(data) == 8
        
        if wifi_avail:
            self.phone_type = PhoneType(struct.unpack('<I', data[0:4])[0])
            self.wifi = struct.unpack('<I', data[4:8])[0]
            print(f"WiFi available, phone type: {self.phone_type.name}, wifi: {self.wifi}")
        else:
            self.phone_type = PhoneType(struct.unpack('<I', data[0:4])[0])
            self.wifi = None
            print(f"No WiFi available, phone type: {self.phone_type.name}")


class Unplugged(Message):
    """Phone unplugged message"""
    
    def __init__(self, header: MessageHeader):
        super().__init__(header)


class AudioData(Message):
    """Audio data message"""
    
    def __init__(self, header: MessageHeader, data: bytes):
        super().__init__(header)
        self.decode_type = struct.unpack('<I', data[0:4])[0]
        self.volume = struct.unpack('<f', data[4:8])[0]
        self.audio_type = struct.unpack('<I', data[8:12])[0]
        
        amount = len(data) - 12
        
        if amount == 1:
            self.command = AudioCommand(struct.unpack('<b', data[12:13])[0])
            self.volume_duration = None
            self.data = None
        elif amount == 4:
            self.command = None
            self.volume_duration = struct.unpack('<f', data[12:16])[0]
            self.data = None
        else:
            self.command = None
            self.volume_duration = None
            # Convert to 16-bit signed integers
            audio_bytes = data[12:]
            sample_count = len(audio_bytes) // 2
            self.data = struct.unpack(f'<{sample_count}h', audio_bytes)


class VideoData(Message):
    """Video data message"""
    
    def __init__(self, header: MessageHeader, data: bytes):
        super().__init__(header)
        self.width = struct.unpack('<I', data[0:4])[0]
        self.height = struct.unpack('<I', data[4:8])[0]
        self.flags = struct.unpack('<I', data[8:12])[0]
        self.length = struct.unpack('<I', data[12:16])[0]
        self.unknown = struct.unpack('<I', data[16:20])[0]
        self.data = data[20:]


class MediaData(Message):
    """Media data message"""
    
    def __init__(self, header: MessageHeader, data: bytes):
        super().__init__(header)
        media_type = struct.unpack('<I', data[0:4])[0]
        
        if media_type == MediaType.AlbumCover:
            image_data = data[4:]
            import base64
            self.payload = {
                'type': media_type,
                'base64_image': base64.b64encode(image_data).decode('ascii')
            }
        elif media_type == MediaType.Data:
            media_data = data[4:-1] if data[-1] == 0 else data[4:]
            try:
                self.payload = {
                    'type': media_type,
                    'media': json.loads(media_data.decode('utf-8'))
                }
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"Error parsing media data: {e}")
                self.payload = None
        else:
            print(f"Unexpected media type: {media_type}")
            self.payload = None


class Opened(Message):
    """Opened message - connection established"""
    
    def __init__(self, header: MessageHeader, data: bytes):
        super().__init__(header)
        self.width = struct.unpack('<I', data[0:4])[0]
        self.height = struct.unpack('<I', data[4:8])[0]
        self.fps = struct.unpack('<I', data[8:12])[0]
        self.format = struct.unpack('<I', data[12:16])[0]
        self.packet_max = struct.unpack('<I', data[16:20])[0]
        self.ibox = struct.unpack('<I', data[20:24])[0]
        self.phone_mode = struct.unpack('<I', data[24:28])[0]


class BoxInfo(Message):
    """Box info message"""
    
    def __init__(self, header: MessageHeader, data: bytes):
        super().__init__(header)
        try:
            self.settings = json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"Error parsing box info: {e}")
            self.settings = {}


class Phase(Message):
    """Phase message"""
    
    def __init__(self, header: MessageHeader, data: bytes):
        super().__init__(header)
        self.phase = struct.unpack('<I', data[0:4])[0]


def create_message(header: MessageHeader, data: Optional[bytes] = None) -> Optional[Message]:
    """Create appropriate Message object based on header type"""
    msg_type = header.type
    
    # Handle messages without data
    if msg_type == MessageType.Unplugged:
        return Unplugged(header)
    
    # Handle messages that might not have data (like HeartBeat response)
    if msg_type == MessageType.HeartBeat:
        return None  # Heartbeat response - ignore
    
    # All other messages require data
    if data is None or len(data) == 0:
        print(f"Warning: No data for message type: {msg_type.name}")
        return None
    
    try:
        # Map message types to classes
        if msg_type == MessageType.AudioData:
            return AudioData(header, data)
        elif msg_type == MessageType.VideoData:
            return VideoData(header, data)
        elif msg_type == MessageType.MediaData:
            return MediaData(header, data)
        elif msg_type == MessageType.BluetoothAddress:
            return BluetoothAddress(header, data)
        elif msg_type == MessageType.BluetoothDeviceName:
            return BluetoothDeviceName(header, data)
        elif msg_type == MessageType.BluetoothPIN:
            return BluetoothPIN(header, data)
        elif msg_type == MessageType.ManufacturerInfo:
            return ManufacturerInfo(header, data)
        elif msg_type == MessageType.SoftwareVersion:
            return SoftwareVersion(header, data)
        elif msg_type == MessageType.Command:
            return Command(header, data)
        elif msg_type == MessageType.Plugged:
            return Plugged(header, data)
        elif msg_type == MessageType.WifiDeviceName:
            return WifiDeviceName(header, data)
        elif msg_type == MessageType.HiCarLink:
            return HiCarLink(header, data)
        elif msg_type == MessageType.BluetoothPairedList:
            return BluetoothPairedList(header, data)
        elif msg_type == MessageType.WifiMacAddress:
            return WifiMacAddress(header, data)
        elif msg_type == MessageType.BluetoothMacAddress:
            return BluetoothMacAddress(header, data)
        elif msg_type == MessageType.EthernetMacAddress:
            return EthernetMacAddress(header, data)
        elif msg_type == MessageType.Open:
            return Opened(header, data)
        elif msg_type == MessageType.BoxSettings:
            return BoxInfo(header, data)
        elif msg_type == MessageType.Phase:
            return Phase(header, data)
        else:
            print(f"Unknown message type: {msg_type.name} ({msg_type:#x}), data length: {len(data) if data else 0}")
            if data and len(data) > 0:
                print(f"  Data preview: {data[:min(32, len(data))].hex()}")
            return None
    except Exception as e:
        print(f"Error creating message of type {msg_type.name}: {e}")
        import traceback
        traceback.print_exc()
        return None
