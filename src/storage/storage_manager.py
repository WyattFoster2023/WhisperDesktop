import os
import sqlite3
from typing import Optional
from src.event_bus.event_bus import EventBus

class StorageManager:
    """
    Handles SQLite database initialization and connection management for transcriptions.
    """
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or os.path.join(os.getcwd(), 'transcriptions.db')
        self._event_bus = EventBus()
        self._initialize_db()

    def _initialize_db(self):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS transcriptions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        text TEXT NOT NULL,
                        segments_metadata TEXT NOT NULL,
                        audio_path TEXT
                    )
                """)
                conn.commit()
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to initialize database: {e}")

    def _get_connection(self):
        """
        Context manager for SQLite connection.
        """
        return sqlite3.connect(self._db_path)

    def save_transcription(self, text: str, segments_metadata: list, audio_path: Optional[str] = None) -> int:
        """
        Save a new transcription to the database.
        Publishes TRANSCRIPTION_SAVED event on success.
        Args:
            text (str): The transcription text
            segments_metadata (list): List of segment metadata dicts
            audio_path (Optional[str]): Path to the audio file
        Returns:
            int: The ID of the saved transcription
        Raises:
            ValueError: If parameters are invalid
            RuntimeError: On database errors
        """
        if not isinstance(text, str) or not text:
            raise ValueError("text must be a non-empty string")
        if not isinstance(segments_metadata, list):
            raise ValueError("segments_metadata must be a list")
        import json
        import datetime
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                timestamp = datetime.datetime.now().isoformat()
                segments_json = json.dumps(segments_metadata)
                cursor.execute(
                    """
                    INSERT INTO transcriptions (timestamp, text, segments_metadata, audio_path)
                    VALUES (?, ?, ?, ?)
                    """,
                    (timestamp, text, segments_json, audio_path)
                )
                transcription_id = cursor.lastrowid
                conn.commit()
                # Publish event
                from src.event_bus.event_bus import EventType
                self._event_bus.publish(EventType.TRANSCRIPTION_COMPLETED, {
                    "id": transcription_id,
                    "timestamp": timestamp,
                    "text": text
                })
                return transcription_id
        except Exception as e:
            raise RuntimeError(f"Failed to save transcription: {e}")

    def get_transcription(self, transcription_id: int) -> Optional[dict]:
        """
        Retrieve a transcription by its ID.
        Args:
            transcription_id (int): The transcription's ID
        Returns:
            dict or None: Transcription data if found, else None
        """
        import json
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, timestamp, text, segments_metadata, audio_path
                    FROM transcriptions
                    WHERE id = ?
                    """,
                    (transcription_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return {
                    "id": row[0],
                    "timestamp": row[1],
                    "text": row[2],
                    "segments_metadata": json.loads(row[3]),
                    "audio_path": row[4]
                }
        except Exception as e:
            raise RuntimeError(f"Failed to get transcription: {e}")

    def get_recent_transcriptions(self, limit: int = 10) -> list:
        """
        Retrieve the most recent transcriptions.
        Args:
            limit (int): Number of transcriptions to return
        Returns:
            list: List of transcription dicts
        """
        import json
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, timestamp, text, segments_metadata, audio_path
                    FROM transcriptions
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (limit,)
                )
                rows = cursor.fetchall()
                return [
                    {
                        "id": row[0],
                        "timestamp": row[1],
                        "text": row[2],
                        "segments_metadata": json.loads(row[3]),
                        "audio_path": row[4]
                    }
                    for row in rows
                ]
        except Exception as e:
            raise RuntimeError(f"Failed to get recent transcriptions: {e}") 