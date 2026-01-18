#!/usr/bin/env python3
"""
Test script for message serialization/deserialization
"""
from messages import MessageHeader, MessageType, VideoData, AudioData, Plugged, PhoneType
from sendable import SendOpen, SendCommand, HeartBeat, SendNumber, FileAddress
from dongle_driver import DongleConfig


def test_header():
    """Test message header serialization"""
    print("Testing MessageHeader...")
    
    # Create header
    header_bytes = MessageHeader.as_buffer(MessageType.HeartBeat, 0)
    print(f"Header bytes ({len(header_bytes)}): {header_bytes.hex()}")
    
    # Parse header
    parsed = MessageHeader.from_buffer(header_bytes)
    print(f"Parsed: type={parsed.type.name}, length={parsed.length}")
    
    assert parsed.type == MessageType.HeartBeat
    assert parsed.length == 0
    print(" Header test passed\n")


def test_sendable():
    """Test sendable messages"""
    print("Testing Sendable Messages...")
    
    # HeartBeat
    hb = HeartBeat()
    hb_bytes = hb.serialise()
    print(f"HeartBeat ({len(hb_bytes)} bytes): {hb_bytes.hex()}")
    
    # SendCommand
    cmd = SendCommand('wifiEnable')
    cmd_bytes = cmd.serialise()
    print(f"SendCommand ({len(cmd_bytes)} bytes): {cmd_bytes.hex()}")
    
    # SendOpen
    config = DongleConfig()
    open_msg = SendOpen(config)
    open_bytes = open_msg.serialise()
    print(f"SendOpen ({len(open_bytes)} bytes): {open_bytes[:32].hex()}...")
    
    # SendNumber
    num = SendNumber(160, FileAddress.DPI)
    num_bytes = num.serialise()
    print(f"SendNumber ({len(num_bytes)} bytes): {num_bytes.hex()}")
    
    print(" Sendable messages test passed\n")


def test_video_data():
    """Test video data parsing"""
    print("Testing VideoData parsing...")
    
    import struct
    
    # Create fake video data
    video_header_data = struct.pack('<IIIII', 1280, 720, 1, 1024, 0)
    video_payload = b'\x00\x01\x02\x03' * 256  # 1024 bytes of fake H264 data
    video_data = video_header_data + video_payload
    
    # Create message header
    msg_header = MessageHeader(len(video_data), MessageType.VideoData)
    
    # Parse
    video_msg = VideoData(msg_header, video_data)
    print(f"Video: {video_msg.width}x{video_msg.height}, {len(video_msg.data)} bytes")
    print(f"Flags: {video_msg.flags}, Length: {video_msg.length}")
    
    assert video_msg.width == 1280
    assert video_msg.height == 720
    assert len(video_msg.data) == 1024
    print(" VideoData test passed\n")


def test_plugged():
    """Test plugged message"""
    print("Testing Plugged message...")
    
    import struct
    
    # Create plugged message with WiFi
    plugged_data = struct.pack('<II', PhoneType.CarPlay, 1)
    msg_header = MessageHeader(len(plugged_data), MessageType.Plugged)
    
    plugged_msg = Plugged(msg_header, plugged_data)
    print(f"Phone type: {plugged_msg.phone_type.name}")
    print(f"WiFi: {plugged_msg.wifi}")
    
    assert plugged_msg.phone_type == PhoneType.CarPlay
    assert plugged_msg.wifi == 1
    print(" Plugged test passed\n")


def test_round_trip():
    """Test serialization and deserialization round trip"""
    print("Testing round-trip...")
    
    # Create a heartbeat message
    hb = HeartBeat()
    serialized = hb.serialise()
    
    # Parse header
    header = MessageHeader.from_buffer(serialized[:16])
    
    print(f"Original type: {MessageType.HeartBeat}")
    print(f"Parsed type: {header.type}")
    print(f"Length: {header.length}")
    
    assert header.type == MessageType.HeartBeat
    assert header.length == 0
    print(" Round-trip test passed\n")


if __name__ == "__main__":
    print("=" * 50)
    print("Message Protocol Tests")
    print("=" * 50 + "\n")
    
    try:
        test_header()
        test_sendable()
        test_video_data()
        test_plugged()
        test_round_trip()
        
        print("=" * 50)
        print("All tests passed! ")
        print("=" * 50)
    except Exception as e:
        print(f"\n Test failed: {e}")
        import traceback
        traceback.print_exc()
