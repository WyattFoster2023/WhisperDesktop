# src/recorder/recorder.py
"""
Recorder module for microphone input, file saving, and crash safety.
"""

from enum import Enum
import pyaudio
import wave
import os
from datetime import datetime
from typing import Optional
from src.event_bus.event_bus import EventBus, EventType

class RecordingMode(Enum):
    PUSH_TO_TALK = 1
    TOGGLE = 2

class Recorder:
    def __init__(self, sample_rate=44100, channels=1, chunk_size=1024, format=pyaudio.paInt16):
        self._sample_rate = sample_rate
        self._channels = channels
        self._chunk_size = chunk_size
        self._format = format
        self._recording = False
        self._audio = pyaudio.PyAudio()
        self._stream = None
        self._file_path = None
        self._event_bus = EventBus()
        self._mode = RecordingMode.TOGGLE
        self._wave_file = None

    # Implementation of methods will follow in subsequent subtasks. 