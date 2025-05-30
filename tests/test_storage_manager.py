import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from src.storage.storage_manager import StorageManager

@pytest.fixture
def temp_db_path(tmp_path):
    path = tmp_path / 'test.db'
    yield str(path)
    # No need to manually delete; tmp_path handles cleanup

def test_db_creation_and_schema(temp_db_path):
    mock_eventbus = MagicMock()
    sm = StorageManager(db_path=temp_db_path, event_bus=mock_eventbus)
    with sm._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transcriptions'")
        assert cursor.fetchone() is not None

def test_save_and_get_transcription(temp_db_path):
    mock_eventbus = MagicMock()
    sm = StorageManager(db_path=temp_db_path, event_bus=mock_eventbus)
    text = "test transcription"
    segments = [{"start": 0, "end": 1, "text": "hello"}]
    audio_path = "/tmp/audio.wav"
    tid = sm.save_transcription(text, segments, audio_path)
    assert isinstance(tid, int)
    result = sm.get_transcription(tid)
    assert result['text'] == text
    assert result['segments_metadata'] == segments
    assert result['audio_path'] == audio_path
    assert mock_eventbus.publish.called

def test_save_invalid_input(temp_db_path):
    mock_eventbus = MagicMock()
    sm = StorageManager(db_path=temp_db_path, event_bus=mock_eventbus)
    with pytest.raises(ValueError):
        sm.save_transcription("", [], None)
    with pytest.raises(ValueError):
        sm.save_transcription("valid", "notalist", None)

def test_get_nonexistent_transcription(temp_db_path):
    mock_eventbus = MagicMock()
    sm = StorageManager(db_path=temp_db_path, event_bus=mock_eventbus)
    assert sm.get_transcription(99999) is None

def test_get_recent_transcriptions(temp_db_path):
    mock_eventbus = MagicMock()
    sm = StorageManager(db_path=temp_db_path, event_bus=mock_eventbus)
    for i in range(5):
        sm.save_transcription(f"t{i}", [{"idx": i}], None)
    recents = sm.get_recent_transcriptions(limit=3)
    assert len(recents) == 3
    assert recents[0]['text'].startswith('t')

def test_update_transcription(temp_db_path):
    mock_eventbus = MagicMock()
    sm = StorageManager(db_path=temp_db_path, event_bus=mock_eventbus)
    text = "original"
    segments = [{"start": 0, "end": 1, "text": "hello"}]
    audio_path = "/tmp/audio.wav"
    tid = sm.save_transcription(text, segments, audio_path)
    # Update text only
    assert sm.update_transcription(tid, text="updated")
    result = sm.get_transcription(tid)
    assert result['text'] == "updated"
    # Update segments only
    new_segments = [{"start": 1, "end": 2, "text": "world"}]
    assert sm.update_transcription(tid, segments_metadata=new_segments)
    result = sm.get_transcription(tid)
    assert result['segments_metadata'] == new_segments
    # Update audio_path only
    assert sm.update_transcription(tid, audio_path="/tmp/other.wav")
    result = sm.get_transcription(tid)
    assert result['audio_path'] == "/tmp/other.wav"
    # Update non-existent
    assert not sm.update_transcription(99999, text="nope")
    assert mock_eventbus.publish.called

def test_delete_transcription(temp_db_path):
    mock_eventbus = MagicMock()
    sm = StorageManager(db_path=temp_db_path, event_bus=mock_eventbus)
    text = "to delete"
    segments = [{"start": 0, "end": 1, "text": "bye"}]
    audio_path = "/tmp/audio2.wav"
    tid = sm.save_transcription(text, segments, audio_path)
    assert sm.delete_transcription(tid)
    assert sm.get_transcription(tid) is None
    # Delete non-existent
    assert not sm.delete_transcription(99999)
    assert mock_eventbus.publish.called

def test_delete_audio_file(tmp_path, temp_db_path):
    mock_eventbus = MagicMock()
    sm = StorageManager(db_path=temp_db_path, event_bus=mock_eventbus)
    # Create a temp file
    audio_file = tmp_path / "audio.wav"
    audio_file.write_bytes(b"test")
    text = "audio test"
    segments = [{"start": 0, "end": 1, "text": "audio"}]
    sm.save_transcription(text, segments, str(audio_file))
    # File exists
    assert sm.delete_audio_file(str(audio_file))
    assert not audio_file.exists()
    # File does not exist
    assert not sm.delete_audio_file(str(audio_file)) 