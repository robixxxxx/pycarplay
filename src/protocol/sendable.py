#!/usr/bin/env python3
"""
Sendable message classes for USB Dongle communication
Based on TypeScript implementation
"""
import struct
import json
import time
from typing import List, Tuple
from enum import IntEnum
from .messages import MessageType, MessageHeader


class CommandMapping(IntEnum):
    """Command mapping enumeration"""
    invalid = 0
    startRecordAudio = 1
    stopRecordAudio = 2
    requestHostUI = 3
    siri = 5
    mic = 7
    boxMic = 15
    enableNightMode = 16
    disableNightMode = 17
    wifi24g = 24
    wifi5g = 25
    left = 100
    right = 101
    frame = 12
    audioTransferOn = 22
    audioTransferOff = 23
    selectDown = 104
    selectUp = 105
    back = 106
    up = 113
    down = 114
    home = 200
    play = 201
    pause = 202
    playOrPause = 203
    next = 204
    prev = 205
    acceptPhone = 300
    rejectPhone = 301
    requestVideoFocus = 500
    releaseVideoFocus = 501
    wifiEnable = 1000
    autoConnetEnable = 1001
    wifiConnect = 1002
    scanningDevice = 1003
    deviceFound = 1004
    deviceNotFound = 1005
    connectDeviceFailed = 1006
    btConnected = 1007
    btDisconnected = 1008
    wifiConnected = 1009
    wifiDisconnected = 1010
    btPairStart = 1011
    wifiPair = 1012


class FileAddress:
    """File addresses for different settings"""
    DPI = '/tmp/screen_dpi'
    NIGHT_MODE = '/tmp/night_mode'
    HAND_DRIVE_MODE = '/tmp/hand_drive_mode'
    CHARGE_MODE = '/tmp/charge_mode'
    BOX_NAME = '/etc/box_name'
    OEM_ICON = '/etc/oem_icon.png'
    AIRPLAY_CONFIG = '/etc/airplay.conf'
    ICON_120 = '/etc/icon_120x120.png'
    ICON_180 = '/etc/icon_180x180.png'
    ICON_250 = '/etc/icon_256x256.png'
    ANDROID_WORK_MODE = '/etc/android_work_mode'


class SendableMessage:
    """Base class for sendable messages"""
    
    def __init__(self, msg_type: MessageType):
        self.type = msg_type
    
    def serialise(self) -> bytes:
        """Serialize message to bytes"""
        return MessageHeader.as_buffer(self.type, 0)


class SendableMessageWithPayload(SendableMessage):
    """Base class for sendable messages with payload"""
    
    def get_payload(self) -> bytes:
        """Get payload bytes - to be implemented by subclasses"""
        raise NotImplementedError()
    
    def serialise(self) -> bytes:
        """Serialize message to bytes"""
        data = self.get_payload()
        byte_length = len(data)
        header = MessageHeader.as_buffer(self.type, byte_length)
        return header + data


class SendCommand(SendableMessageWithPayload):
    """Send command message"""
    
    def __init__(self, command: str):
        super().__init__(MessageType.Command)
        self.value = CommandMapping[command]
    
    def get_payload(self) -> bytes:
        return struct.pack('<I', self.value)


class TouchAction(IntEnum):
    """Touch action enumeration"""
    Down = 14
    Move = 15
    Up = 16


class SendTouch(SendableMessageWithPayload):
    """Send touch event"""
    
    def __init__(self, x: float, y: float, action: TouchAction):
        super().__init__(MessageType.Touch)
        self.x = x
        self.y = y
        self.action = action
    
    def get_payload(self) -> bytes:
        # Clamp values between 0 and 1, then scale to 10000
        final_x = max(0, min(10000, int(10000 * self.x)))
        final_y = max(0, min(10000, int(10000 * self.y)))
        
        return struct.pack('<IIII', self.action, final_x, final_y, 0)


class MultiTouchAction(IntEnum):
    """Multi-touch action enumeration"""
    Up = 0
    Down = 1
    Move = 2


class TouchItem:
    """Individual touch item for multi-touch"""
    
    def __init__(self, x: float, y: float, action: MultiTouchAction, touch_id: int):
        self.x = x
        self.y = y
        self.action = action
        self.id = touch_id
    
    def get_payload(self) -> bytes:
        return struct.pack('<ffII', self.x, self.y, self.action, self.id)


class SendMultiTouch(SendableMessageWithPayload):
    """Send multi-touch event"""
    
    def __init__(self, touch_data: List[Tuple[float, float, MultiTouchAction]]):
        super().__init__(MessageType.MultiTouch)
        self.touches = [
            TouchItem(x, y, action, index)
            for index, (x, y, action) in enumerate(touch_data)
        ]
    
    def get_payload(self) -> bytes:
        return b''.join(touch.get_payload() for touch in self.touches)


class SendAudio(SendableMessageWithPayload):
    """Send audio data"""
    
    def __init__(self, data: bytes):
        super().__init__(MessageType.AudioData)
        self.data = data
    
    def get_payload(self) -> bytes:
        # Audio header: decodeType=5, volume=0.0, audioType=3
        audio_header = struct.pack('<IfI', 5, 0.0, 3)
        return audio_header + self.data


class SendFile(SendableMessageWithPayload):
    """Send file content"""
    
    def __init__(self, content: bytes, file_name: str):
        super().__init__(MessageType.SendFile)
        self.content = content
        self.file_name = file_name
    
    def get_payload(self) -> bytes:
        # File name with null terminator
        file_name_bytes = (self.file_name + '\0').encode('ascii')
        name_length = struct.pack('<I', len(file_name_bytes))
        content_length = struct.pack('<I', len(self.content))
        
        return name_length + file_name_bytes + content_length + self.content


class SendNumber(SendFile):
    """Send number to file"""
    
    def __init__(self, content: int, file: str):
        message = struct.pack('<I', content)
        super().__init__(message, file)


class SendBoolean(SendNumber):
    """Send boolean to file"""
    
    def __init__(self, content: bool, file: str):
        super().__init__(1 if content else 0, file)


class SendString(SendFile):
    """Send string to file"""
    
    def __init__(self, content: str, file: str):
        if len(content) > 16:
            print("Warning: string too long, truncating to 16 characters")
            content = content[:16]
        message = content.encode('ascii')
        super().__init__(message, file)


class HeartBeat(SendableMessage):
    """Heartbeat message"""
    
    def __init__(self):
        super().__init__(MessageType.HeartBeat)


class SendDisconnectPhone(SendableMessage):
    """Send disconnect phone command"""
    
    def __init__(self):
        super().__init__(MessageType.DisconnectPhone)


class SendOpen(SendableMessageWithPayload):
    """Send open/init message"""
    
    def __init__(self, config):
        super().__init__(MessageType.Open)
        self.config = config
    
    def get_payload(self) -> bytes:
        return struct.pack(
            '<IIIIIII',
            self.config.width,
            self.config.height,
            self.config.fps,
            self.config.format,
            self.config.packet_max,
            self.config.ibox_version,
            self.config.phone_work_mode
        )


class SendBoxSettings(SendableMessageWithPayload):
    """Send box settings"""
    
    def __init__(self, config, sync_time: int = None):
        super().__init__(MessageType.BoxSettings)
        self.config = config
        self.sync_time = sync_time
    
    def get_payload(self) -> bytes:
        settings = {
            'mediaDelay': self.config.media_delay,
            'syncTime': self.sync_time if self.sync_time is not None else int(time.time()),
            'androidAutoSizeW': self.config.width,
            'androidAutoSizeH': self.config.height,
        }
        return json.dumps(settings).encode('ascii')


class LogoType(IntEnum):
    """Logo type enumeration"""
    HomeButton = 1
    Siri = 2


class SendLogoType(SendableMessageWithPayload):
    """Send logo type"""
    
    def __init__(self, logo_type: LogoType):
        super().__init__(MessageType.LogoType)
        self.logo_type = logo_type
    
    def get_payload(self) -> bytes:
        return struct.pack('<I', self.logo_type)


class SendIconConfig(SendFile):
    """Send icon configuration"""
    
    def __init__(self, config: dict):
        value_map = {
            'oemIconVisible': 1,
            'name': 'AutoBox',
            'model': 'Magic-Car-Link-1.00',
            'oemIconPath': FileAddress.OEM_ICON,
        }
        
        if 'label' in config:
            value_map['oemIconLabel'] = config['label']
        
        file_data = '\n'.join(f"{k} = {v}" for k, v in value_map.items()) + '\n'
        super().__init__(file_data.encode('ascii'), FileAddress.AIRPLAY_CONFIG)


class SendCloseDongle(SendableMessage):
    """Close dongle - disconnects phone and closes dongle"""
    
    def __init__(self):
        super().__init__(MessageType.CloseDongle)


class SendDisconnectPhone(SendableMessage):
    """Disconnect phone - phone can reconnect without reopening dongle"""
    
    def __init__(self):
        super().__init__(MessageType.DisconnectPhone)
