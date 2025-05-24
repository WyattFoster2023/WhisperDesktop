import asyncio
import wave
import numpy as np
import pyaudio
from typing import Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime

@dataclass
class AudioChunk:
    data: bytes
    timestamp: datetime
    duration: float

class AudioManager:
    def __init__(self, 
                 sample_rate: int = 16000,
                 chunk_size: int = 1024,
                 channels: int = 1,
                 format: int = pyaudio.paInt16):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.format = format
        self.audio = pyaudio.PyAudio()
        
        # List available input devices
        print("\n=== Available Audio Input Devices ===")
        default_input = self.audio.get_default_input_device_info()
        print(f"Default input device: {default_input['name']}")
        
        for i in range(self.audio.get_device_count()):
            dev_info = self.audio.get_device_info_by_index(i)
            if dev_info['maxInputChannels'] > 0:  # Only show input devices
                print(f"Device {i}: {dev_info['name']}")
        print("=====================================\n")
        
        self.stream: Optional[pyaudio.Stream] = None
        self.recording = False
        self.chunks: List[AudioChunk] = []
        self.on_chunk_callback: Optional[Callable[[AudioChunk], None]] = None
        
    def start_recording(self):
        """Start recording audio."""
        if self.recording:
            return
            
        self.recording = True
        self.chunks = []
        
        def callback(in_data, frame_count, time_info, status):
            if self.recording:
                chunk = AudioChunk(
                    data=in_data,
                    timestamp=datetime.now(),
                    duration=frame_count / self.sample_rate
                )
                self.chunks.append(chunk)
                if self.on_chunk_callback:
                    self.on_chunk_callback(chunk)
            return (in_data, pyaudio.paContinue)
        
        try:
            # Get default input device info
            default_input = self.audio.get_default_input_device_info()
            print(f"[DEBUG] Using input device: {default_input['name']}")
            
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=default_input['index'],  # Use default input device
                frames_per_buffer=self.chunk_size,
                stream_callback=callback
            )
            self.stream.start_stream()
            print("[DEBUG] Audio stream started successfully")
        except Exception as e:
            print(f"[ERROR] Failed to start audio stream: {e}")
            self.recording = False
            raise
    
    def stop_recording(self) -> bytes:
        """Stop recording and return the complete audio data."""
        if not self.recording:
            return b''
            
        self.recording = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        # Combine all chunks
        audio_data = b''.join(chunk.data for chunk in self.chunks)
        return audio_data
    
    def add_chunk(self, chunk: AudioChunk):
        """Add a chunk of audio data."""
        self.chunks.append(chunk)
        if self.on_chunk_callback:
            self.on_chunk_callback(chunk)
    
    def save_to_wav(self, audio_data: bytes, filename: str):
        """Save audio data to a WAV file."""
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data)
    
    def cleanup(self):
        """Clean up audio resources."""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()
    
    def get_audio_level(self, chunk: bytes) -> float:
        """Calculate the audio level from a chunk of audio data."""
        audio_data = np.frombuffer(chunk, dtype=np.int16)
        return float(np.abs(audio_data).mean()) / 32768.0 