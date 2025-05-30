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
from whisperdesktop.event_bus.event_bus import EventBus, EventType
from whisperdesktop.utils.logger import Logger

logger = Logger()

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
        self._logger = Logger()

    # Implementation of methods will follow in subsequent subtasks. 

    def start_recording(self, mode=RecordingMode.TOGGLE):
        if self._recording:
            self._logger.warning("Recording already in progress.")
            return
        try:
            self._mode = mode
            self._recording = True
            os.makedirs('recordings', exist_ok=True)
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            self._file_path = f'recordings/recording_{timestamp}.wav'
            self._wave_file = wave.open(self._file_path, 'wb')
            self._wave_file.setnchannels(self._channels)
            self._wave_file.setsampwidth(self._audio.get_sample_size(self._format))
            self._wave_file.setframerate(self._sample_rate)
            self._stream = self._audio.open(
                format=self._format,
                channels=self._channels,
                rate=self._sample_rate,
                input=True,
                frames_per_buffer=self._chunk_size,
                stream_callback=self._audio_callback
            )
            self._event_bus.publish(EventType.RECORDING_STARTED, self._file_path)
            self._logger.info(f"Started recording: {self._file_path}")
        except Exception as e:
            self._logger.error(f"Error starting recording: {e}")
            self._recording = False

    def _audio_callback(self, in_data, frame_count, time_info, status):
        try:
            self._wave_file.writeframes(in_data)
        except Exception as e:
            self._logger.error(f"Error writing audio data: {e}")
        return (in_data, pyaudio.paContinue)

    def stop_recording(self):
        if not self._recording:
            self._logger.warning("No recording in progress to stop.")
            return
        try:
            self._recording = False
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None
            if self._wave_file:
                self._wave_file.close()
                self._wave_file = None
            self._event_bus.get_queue('transcription').put(self._file_path)
            self._event_bus.publish(EventType.RECORDING_STOPPED, self._file_path)
            self._logger.info(f"Stopped recording: {self._file_path}")
            return self._file_path
        except Exception as e:
            self._logger.error(f"Error stopping recording: {e}")

    def toggle_recording(self):
        if self._recording:
            return self.stop_recording()
        else:
            return self.start_recording(RecordingMode.TOGGLE)

    def cleanup(self):
        try:
            if self._recording:
                self.stop_recording()
            self._audio.terminate()
            self._logger.info("Recorder cleaned up and PyAudio terminated.")
        except Exception as e:
            self._logger.error(f"Error during cleanup: {e}") 