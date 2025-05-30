import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from unittest.mock import patch, MagicMock
from src.recorder.recorder import Recorder, RecordingMode

@patch('src.recorder.recorder.pyaudio.PyAudio')
@patch('src.recorder.recorder.wave.open')
@patch('src.recorder.recorder.EventBus')
def test_start_stop_recording(mock_eventbus, mock_wave_open, mock_pyaudio):
    mock_stream = MagicMock()
    mock_audio = MagicMock()
    mock_audio.open.return_value = mock_stream
    mock_pyaudio.return_value = mock_audio
    mock_wave = MagicMock()
    mock_wave_open.return_value = mock_wave
    recorder = Recorder()
    recorder.start_recording(RecordingMode.TOGGLE)
    assert recorder._recording is True
    assert os.path.basename(recorder._file_path).startswith('recording_')
    recorder.stop_recording()
    assert recorder._recording is False
    mock_wave.close.assert_called()
    mock_stream.stop_stream.assert_called()
    mock_stream.close.assert_called()

@patch('src.recorder.recorder.pyaudio.PyAudio')
@patch('src.recorder.recorder.wave.open')
@patch('src.recorder.recorder.EventBus')
def test_toggle_recording(mock_eventbus, mock_wave_open, mock_pyaudio):
    mock_stream = MagicMock()
    mock_audio = MagicMock()
    mock_audio.open.return_value = mock_stream
    mock_pyaudio.return_value = mock_audio
    mock_wave = MagicMock()
    mock_wave_open.return_value = mock_wave
    recorder = Recorder()
    recorder.toggle_recording()
    assert recorder._recording is True
    recorder.toggle_recording()
    assert recorder._recording is False

@patch('src.recorder.recorder.pyaudio.PyAudio')
@patch('src.recorder.recorder.wave.open')
def test_eventbus_integration(mock_wave_open, mock_pyaudio):
    from src.recorder.recorder import Recorder, RecordingMode
    from src.event_bus.event_bus import EventBus, EventType
    mock_stream = MagicMock()
    mock_audio = MagicMock()
    mock_audio.open.return_value = mock_stream
    mock_pyaudio.return_value = mock_audio
    mock_wave = MagicMock()
    mock_wave_open.return_value = mock_wave
    recorder = Recorder()
    events = []
    bus = recorder._event_bus
    bus.subscribe(EventType.RECORDING_STARTED, lambda payload: events.append(('started', payload)))
    bus.subscribe(EventType.RECORDING_STOPPED, lambda payload: events.append(('stopped', payload)))
    recorder.start_recording(RecordingMode.TOGGLE)
    recorder.stop_recording()
    assert events[0][0] == 'started'
    assert events[1][0] == 'stopped' 