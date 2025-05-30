import os
import sqlite3
from typing import Optional
from src.event_bus.event_bus import EventBus
from src.utils.logger import Logger

class StorageManager:
    """
    Handles SQLite database initialization and connection management for transcriptions.
    """
    def __init__(self, db_path: Optional[str] = None, event_bus: Optional[EventBus] = None):
        self._db_path = db_path or os.path.join(os.getcwd(), 'transcriptions.db')
        self._event_bus = event_bus if event_bus is not None else EventBus()
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
            Logger().error(f"Failed to initialize database: {e}")

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
            Logger().error(f"Failed to save transcription: {e}")
            return -1

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
            Logger().error(f"Failed to get transcription: {e}")
            return None

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
            Logger().error(f"Failed to get recent transcriptions: {e}")
            return []

    def update_transcription(self, transcription_id: int, text: Optional[str] = None, segments_metadata: Optional[list] = None, audio_path: Optional[str] = None) -> bool:
        """
        Update an existing transcription's fields. Publishes TRANSCRIPTION_COMPLETED event on success.
        Args:
            transcription_id (int): The ID of the transcription to update
            text (Optional[str]): New transcription text
            segments_metadata (Optional[list]): New segments metadata
            audio_path (Optional[str]): New audio file path
        Returns:
            bool: True if update succeeded, False otherwise
        Raises:
            RuntimeError: On database errors
        """
        import json
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                fields = []
                values = []
                if text is not None:
                    fields.append("text = ?")
                    values.append(text)
                if segments_metadata is not None:
                    fields.append("segments_metadata = ?")
                    values.append(json.dumps(segments_metadata))
                if audio_path is not None:
                    fields.append("audio_path = ?")
                    values.append(audio_path)
                if not fields:
                    return False
                values.append(transcription_id)
                query = f"UPDATE transcriptions SET {', '.join(fields)} WHERE id = ?"
                cursor.execute(query, tuple(values))
                if cursor.rowcount == 0:
                    return False
                conn.commit()
                # Publish event (no specific update event, use COMPLETED)
                from src.event_bus.event_bus import EventType
                self._event_bus.publish(EventType.TRANSCRIPTION_COMPLETED, {"id": transcription_id})
                return True
        except Exception as e:
            raise RuntimeError(f"Failed to update transcription: {e}")

    def delete_transcription(self, transcription_id: int) -> bool:
        """
        Delete a transcription from the database. Publishes TRANSCRIPTION_COMPLETED event on success.
        Args:
            transcription_id (int): The ID of the transcription to delete
        Returns:
            bool: True if deletion succeeded, False otherwise
        Raises:
            RuntimeError: On database errors
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM transcriptions WHERE id = ?", (transcription_id,))
                if cursor.rowcount == 0:
                    return False
                conn.commit()
                # Publish event (no specific delete event, use COMPLETED)
                from src.event_bus.event_bus import EventType
                self._event_bus.publish(EventType.TRANSCRIPTION_COMPLETED, {"id": transcription_id})
                return True
        except Exception as e:
            raise RuntimeError(f"Failed to delete transcription: {e}")

    def delete_audio_file(self, audio_path: str) -> bool:
        """
        Delete an audio file from the filesystem and update the database. Sets audio_path to NULL in the DB.
        Args:
            audio_path (str): Path to the audio file
        Returns:
            bool: True if file deleted and DB updated, False otherwise
        """
        if not audio_path or not os.path.exists(audio_path):
            return False
        try:
            os.remove(audio_path)
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE transcriptions SET audio_path = NULL WHERE audio_path = ?", (audio_path,))
                conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting audio file: {e}")
            return False 