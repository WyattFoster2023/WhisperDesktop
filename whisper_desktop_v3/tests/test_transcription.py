import pytest
import os
import numpy as np
from whisper_desktop.transcription import TranscriptionManager
from whisper_desktop.database import DatabaseManager
import asyncio
from pydub import AudioSegment

@pytest.fixture
def db_manager():
    return DatabaseManager()

@pytest.fixture
def transcription_manager(db_manager):
    return TranscriptionManager(db_manager=db_manager)

@pytest.fixture
def test_audio_path():
    return os.path.join(os.path.dirname(__file__), "..", "test_material", "recording_1.m4a")

@pytest.fixture
def expected_transcription():
    with open(os.path.join(os.path.dirname(__file__), "..", "test_material", "transcription_1.txt"), 'r') as f:
        return f.read().strip()

@pytest.mark.asyncio
async def test_transcription_accuracy(transcription_manager, test_audio_path, expected_transcription):
    """Test that the transcription manager correctly transcribes audio."""
    # Start the transcription processing loop
    processing_task = asyncio.create_task(transcription_manager.start_processing())

    # Load audio file using pydub
    audio = AudioSegment.from_file(test_audio_path)
    audio = audio.set_channels(1).set_frame_rate(16000)
    audio_data = np.array(audio.get_array_of_samples()).astype(np.float32) / (2 ** 15)
    
    # Add audio to transcription manager
    await transcription_manager.add_audio(audio_data)
    
    # Wait for the queue to be processed
    await asyncio.sleep(2)  # Give time for processing (tune as needed)
    transcription = await transcription_manager.get_transcription()
    
    # Stop the processing loop
    await transcription_manager.stop_processing()
    await processing_task
    
    # Compare with expected transcription
    assert transcription.strip() == expected_transcription, \
        f"Transcription mismatch.\nExpected: {expected_transcription}\nGot: {transcription}"

@pytest.mark.asyncio
async def test_transcription_manager_initialization(transcription_manager):
    """Test that the transcription manager initializes correctly."""
    assert transcription_manager is not None
    assert transcription_manager.db_manager is not None

@pytest.mark.asyncio
async def test_empty_audio_handling(transcription_manager):
    """Test that the transcription manager handles empty audio correctly."""
    empty_audio = np.zeros(1000, dtype=np.float32)
    await transcription_manager.add_audio(empty_audio)
    transcription = await transcription_manager.get_transcription()
    assert transcription == ""  # Empty audio should result in empty transcription 

@pytest.mark.asyncio
async def test_transcription_pipeline(transcription_manager):
    """Test the complete transcription pipeline with simulated audio."""
    # Start the transcription processing loop
    processing_task = asyncio.create_task(transcription_manager.start_processing())
    
    # Create simulated audio data
    audio_data = np.random.randint(-32768, 32767, 16000, dtype=np.int16).tobytes()
    
    # Add audio to transcription manager
    await transcription_manager.add_audio(audio_data)
    
    # Wait for processing
    await asyncio.sleep(2)
    
    # Get transcription
    transcription = await transcription_manager.get_transcription()
    
    # Stop processing
    await transcription_manager.stop_processing()
    await processing_task
    
    # Verify we got a transcription (even if empty)
    assert transcription is not None 