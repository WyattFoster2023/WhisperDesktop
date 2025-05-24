import sqlite3
from datetime import datetime
from typing import List, Optional, Tuple

class DatabaseManager:
    def __init__(self, db_path: str = "transcriptions.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transcriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    duration FLOAT,
                    mode TEXT
                )
            """)
            conn.commit()
    
    def add_transcription(self, text: str, duration: float, mode: str) -> int:
        """Add a new transcription to the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO transcriptions (text, timestamp, duration, mode)
                VALUES (?, ?, ?, ?)
            """, (text, datetime.now(), duration, mode))
            conn.commit()
            return cursor.lastrowid
    
    def get_recent_transcriptions(self, limit: int = 50) -> List[Tuple]:
        """Get the most recent transcriptions."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, text, timestamp, duration, mode
                FROM transcriptions
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            return cursor.fetchall()
    
    def get_transcription(self, transcription_id: int) -> Optional[Tuple]:
        """Get a specific transcription by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, text, timestamp, duration, mode
                FROM transcriptions
                WHERE id = ?
            """, (transcription_id,))
            return cursor.fetchone()
    
    def delete_transcription(self, transcription_id: int) -> bool:
        """Delete a transcription by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM transcriptions
                WHERE id = ?
            """, (transcription_id,))
            conn.commit()
            return cursor.rowcount > 0 