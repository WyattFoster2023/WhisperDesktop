import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from ..gui import TranscriptionGUI, StatusIndicator
import sys
import asyncio
import numpy as np

@pytest.fixture(scope="session")
def app():
    app = QApplication(sys.argv)
    yield app
    app.quit()

@pytest.fixture
def gui(app):
    gui = TranscriptionGUI()
    yield gui
    gui.close()

def test_ptt_button_press_release(gui):
    """Test that PTT button press and release triggers recording."""
    # Press PTT button
    QTest.mousePress(gui.ptt_button, Qt.MouseButton.LeftButton)
    assert gui.audio_manager.recording
    
    # Release PTT button
    QTest.mouseRelease(gui.ptt_button, Qt.MouseButton.LeftButton)
    assert not gui.audio_manager.recording

def test_ptt_hotkey(gui):
    """Test that PTT hotkey triggers recording."""
    # Set PTT hotkey
    gui.ptt_hotkey.setText("Ctrl+Shift+R")
    
    # Simulate hotkey press
    gui.start_recording()
    assert gui.audio_manager.recording
    
    # Simulate hotkey release
    gui.stop_recording()
    assert not gui.audio_manager.recording

def test_transcription_callback(gui):
    """Test that transcription callback updates the GUI."""
    test_text = "Test transcription"
    
    # Call the transcription callback
    gui._on_transcription(test_text)
    
    # Check if text was added to log
    assert test_text in gui.transcription_log.toPlainText()

def test_waveform_update(gui):
    """Test that waveform updates with audio level."""
    # Simulate audio chunk as bytes
    test_data = np.random.randint(-32768, 32767, 1024, dtype=np.int16).tobytes()
    gui._on_audio_chunk(test_data)
    # Check if waveform data was updated
    assert not np.all(gui.waveform.data == 0)

@pytest.mark.asyncio
async def test_transcription_worker(gui):
    """Test that the GUI's transcription worker processes audio data."""
    # Create simulated audio data
    audio_data = np.random.randint(-32768, 32767, 16000, dtype=np.int16).tobytes()
    
    # Add audio to queue
    gui.audio_queue.put(audio_data)
    
    # Wait for processing
    await asyncio.sleep(2)
    
    # Verify transcription manager received the audio
    assert gui.transcription_manager._last_transcription is not None 

@pytest.mark.asyncio
async def test_ptt_workflow(gui):
    """Test the complete PTT workflow from recording to transcription."""
    # Start recording
    gui.start_recording()
    assert gui.audio_manager.recording
    # Simulate some audio data as bytes
    test_data = np.random.randint(-32768, 32767, 16000, dtype=np.int16).tobytes()
    gui._on_audio_chunk(test_data)
    # Stop recording
    gui.stop_recording()
    assert not gui.audio_manager.recording
    # Wait for processing
    await asyncio.sleep(2)
    # Verify transcription was processed
    assert gui.transcription_manager._last_transcription is not None 

def test_status_indicator(app):
    indicator = StatusIndicator()
    assert indicator.status == False
    
    indicator.set_status(True)
    assert indicator.status == True
    
    indicator.set_status(False)
    assert indicator.status == False

def test_gui_status_indicators(gui):
    # Check initial states
    assert gui.model_status.status == False
    assert gui.trans_status.status == False
    
    # Simulate model loading completion
    gui.model_status.set_status(True)
    assert gui.model_status.status == True
    
    # Simulate transcription start
    gui.trans_status.set_status(True)
    assert gui.trans_status.status == True
    
    # Simulate transcription completion
    gui.trans_status.set_status(False)
    assert gui.trans_status.status == False 