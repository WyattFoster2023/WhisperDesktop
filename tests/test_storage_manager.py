import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from src.storage.storage_manager import StorageManager

@pytest.fixture
def temp_db_path():
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)

@patch('src.storage.storage_manager.EventBus')
def test_db_creation_and_schema(mock_eventbus, temp_db_path):
    sm = StorageManager(db_path=temp_db_path)
    # Should not raise, table should exist
    with sm._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transcriptions'")
        assert cursor.fetchone() is not None

@patch('src.storage.storage_manager.EventBus')
def test_save_and_get_transcription(mock_eventbus, temp_db_path):
    sm = StorageManager(db_path=temp_db_path)
    text = "test transcription"
    segments = [{"start": 0, "end": 1, "text": "hello"}]
    audio_path = "/tmp/audio.wav"
    mock_event = MagicMock()
    mock_event.publish = MagicMock()
    mock_eventbus.return_value = mock_event
    tid = sm.save_transcription(text, segments, audio_path)
    assert isinstance(tid, int)
    result = sm.get_transcription(tid)
    assert result['text'] == text
    assert result['segments_metadata'] == segments
    assert result['audio_path'] == audio_path
    mock_event.publish.assert_called()

@patch('src.storage.storage_manager.EventBus')
def test_save_invalid_input(mock_eventbus, temp_db_path):
    sm = StorageManager(db_path=temp_db_path)
    with pytest.raises(ValueError):
        sm.save_transcription("", [], None)
    with pytest.raises(ValueError):
        sm.save_transcription("valid", "notalist", None)

@patch('src.storage.storage_manager.EventBus')
def test_get_nonexistent_transcription(mock_eventbus, temp_db_path):
    sm = StorageManager(db_path=temp_db_path)
    assert sm.get_transcription(99999) is None

@patch('src.storage.storage_manager.EventBus')
def test_get_recent_transcriptions(mock_eventbus, temp_db_path):
    sm = StorageManager(db_path=temp_db_path)
    for i in range(5):
        sm.save_transcription(f"t{i}", [{"idx": i}], None)
    recents = sm.get_recent_transcriptions(limit=3)
    assert len(recents) == 3
    assert recents[0]['text'].startswith('t') 