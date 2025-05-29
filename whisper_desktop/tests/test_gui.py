import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from ..gui import TranscriptionGUI, StatusIndicator
import sys
import asyncio
import numpy as np
from whisper_desktop.database import DatabaseManager
from whisper_desktop.transcription import TranscriptionManager

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

def test_record_button_press_release(gui):
    """Test that the record button toggles recording state."""
    # Initial state
    assert not gui.is_recording
    
    # Press button
    QTest.mouseClick(gui.record_button, Qt.MouseButton.LeftButton)
    assert gui.is_recording
    
    # Release button
    QTest.mouseClick(gui.record_button, Qt.MouseButton.LeftButton)
    assert not gui.is_recording

def test_record_hotkey(gui):
    """Test that the record hotkey toggles recording state."""
    # Initial state
    assert not gui.is_recording
    
    # Press hotkey
    QTest.keyClick(gui, Qt.Key.Key_Space)
    assert gui.is_recording
    
    # Press hotkey again
    QTest.keyClick(gui, Qt.Key.Key_Space)
    assert not gui.is_recording

def test_transcription_callback(gui):
    """Test that transcriptions are displayed correctly."""
    test_text = "Test transcription"
    gui.on_transcription(test_text)
    assert test_text in gui.transcription_text.toPlainText()

def test_waveform_update(gui):
    """Test that the waveform is updated with audio data."""
    # Simulate audio data
    audio_data = b'\x00' * 1024
    gui.on_audio_chunk(audio_data)
    assert gui.waveform is not None

def test_transcription_worker(gui):
    """Test that the transcription worker processes audio correctly."""
    # Start recording
    gui.start_recording()
    assert gui.is_recording
    
    # Simulate audio data
    audio_data = b'\x00' * 1024
    gui.on_audio_chunk(audio_data)
    
    # Stop recording
    gui.stop_recording()
    assert not gui.is_recording

def test_recording_workflow(gui):
    """Test the complete recording workflow."""
    # Start recording
    gui.start_recording()
    assert gui.is_recording
    
    # Simulate audio chunks
    for _ in range(3):
        audio_data = b'\x00' * 1024
        gui.on_audio_chunk(audio_data)
    
    # Stop recording
    gui.stop_recording()
    assert not gui.is_recording
    
    # Verify waveform was updated
    assert gui.waveform is not None

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

def test_settings_update(gui):
    """Test that settings updates are reflected in the GUI."""
    # Update settings
    gui.model_combo.setCurrentText("small")
    gui.device_combo.setCurrentText("cpu")
    gui.compute_combo.setCurrentText("float16")
    gui.save_settings()
    
    # Verify settings were updated
    assert gui.settings.model == "small"
    assert gui.settings.device == "cpu"
    assert gui.settings.compute_type == "float16" 