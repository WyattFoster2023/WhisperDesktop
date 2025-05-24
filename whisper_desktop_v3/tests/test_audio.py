import pytest
import numpy as np
from whisper_desktop.audio import AudioManager
import asyncio
import threading
import time

@pytest.fixture
def audio_manager():
    return AudioManager()

def test_audio_recording(audio_manager):
    """Test that audio recording captures data."""
    # Start recording
    audio_manager.start_recording()
    
    # Simulate some audio data
    test_data = np.random.randint(-32768, 32767, 1024, dtype=np.int16).tobytes()
    audio_manager.chunks.append(type('AudioChunk', (), {
        'data': test_data,
        'timestamp': time.time(),
        'duration': 0.1
    }))
    
    # Stop recording and get data
    audio_data = audio_manager.stop_recording()
    
    # Verify we got audio data
    assert len(audio_data) > 0
    assert isinstance(audio_data, bytes)

def test_audio_level_calculation(audio_manager):
    """Test that audio level is calculated correctly."""
    # Create test audio data
    test_data = np.random.randint(-32768, 32767, 1024, dtype=np.int16).tobytes()
    
    # Calculate level
    level = audio_manager.get_audio_level(test_data)
    
    # Verify level is between 0 and 1
    assert 0 <= level <= 1

def test_recording_state(audio_manager):
    """Test recording state management."""
    assert not audio_manager.recording
    
    audio_manager.start_recording()
    assert audio_manager.recording
    
    audio_manager.stop_recording()
    assert not audio_manager.recording

def test_chunk_callback(audio_manager):
    """Test that chunk callback is called during recording."""
    callback_called = False
    
    def on_chunk(chunk):
        nonlocal callback_called
        callback_called = True
    
    audio_manager.on_chunk_callback = on_chunk
    audio_manager.start_recording()
    
    # Simulate some audio data
    test_data = np.random.randint(-32768, 32767, 1024, dtype=np.int16).tobytes()
    chunk = type('AudioChunk', (), {
        'data': test_data,
        'timestamp': time.time(),
        'duration': 0.1
    })
    
    # Add chunk using the new method
    audio_manager.add_chunk(chunk)
    
    # Give time for callback
    time.sleep(0.1)
    
    audio_manager.stop_recording()
    assert callback_called 