#!/usr/bin/env python3
"""
Media Logger for CarPlay

Logs CarPlay media events (music, navigation, phone calls) to JSONL files
for analysis and debugging. Each log entry is timestamped and structured
for easy parsing.
"""
from datetime import datetime
import json
import os


class MediaLogger:
    """Logs CarPlay media events to timestamped JSONL files
    
    Features:
    - Auto-creates log directory
    - One log file per session with timestamp
    - JSONL format (one JSON object per line)
    - Automatic file flushing for reliability
    """
    
    def __init__(self, log_dir="logs"):
        """Initialize media logger
        
        Args:
            log_dir: Directory for log files (default: "logs")
        """
        self.log_dir = log_dir
        self.enabled = False
        self.log_file = None
        
        # Create logs directory if needed
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
    
    # === Public API ===
    
    def start(self):
        """Start logging to new timestamped file
        
        Creates file: carplay_media_YYYYMMDD_HHMMSS.jsonl
        """
        if self.enabled:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(self.log_dir, f"carplay_media_{timestamp}.jsonl")
        self.log_file = open(log_path, 'w')
        self.enabled = True
        print(f" Media logging started: {log_path}")
    
    def stop(self):
        """Stop logging and close file"""
        if self.log_file:
            self.log_file.close()
            self.log_file = None
        self.enabled = False
        print(f" Media logging stopped")
    
    def log_music(self, song, artist, album, play_time_ms, duration_ms):
        """Log music playback event
        
        Args:
            song: Song title
            artist: Artist name
            album: Album name
            play_time_ms: Current playback position
            duration_ms: Total song duration
        """
        if not self.enabled:
            return
        
        self._write_entry({
            'type': 'music',
            'song': song,
            'artist': artist,
            'album': album,
            'play_time_ms': play_time_ms,
            'duration_ms': duration_ms
        })
    
    def log_navigation(self, current_road, next_road, distance, distance_unit, maneuver, eta):
        """Log navigation event
        
        Args:
            current_road: Current road name
            next_road: Next road name
            distance: Distance to next maneuver
            distance_unit: Unit (m, km, mi, etc.)
            maneuver: Maneuver type
            eta: Estimated time of arrival
        """
        if not self.enabled:
            return
        
        self._write_entry({
            'type': 'navigation',
            'current_road': current_road,
            'next_road': next_road,
            'distance': distance,
            'distance_unit': distance_unit,
            'maneuver': maneuver,
            'eta': eta
        })
    
    def log_phone_call(self, status, caller):
        """Log phone call event
        
        Args:
            status: Call status (incoming, active, ended, etc.)
            caller: Caller name/number
        """
        if not self.enabled:
            return
        
        self._write_entry({
            'type': 'phone_call',
            'status': status,
            'caller': caller
        })
    
    def log_raw(self, data_type, data):
        """Log raw data event
        
        Args:
            data_type: Type identifier
            data: Raw data (will be JSON serialized)
        """
        if not self.enabled:
            return
        
        self._write_entry({
            'type': data_type,
            'data': data
        })
    
    # === Internal Methods ===
    
    def _write_entry(self, entry: dict):
        """Write log entry to file
        
        Adds timestamp and flushes immediately for reliability.
        
        Args:
            entry: Dictionary to log
        """
        entry['timestamp'] = datetime.now().isoformat()
        self.log_file.write(json.dumps(entry) + '\n')
        self.log_file.flush()

