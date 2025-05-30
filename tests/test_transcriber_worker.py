import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from unittest.mock import patch, MagicMock
import multiprocessing
from src.transcriber.transcriber_worker import TranscriberWorker
import os
import shutil
import tempfile
import subprocess
from pathlib import Path
from src.event_bus.event_bus import EventBus
import json
from datetime import datetime

def soft_equal(a, b):
    import re
    def norm(s):
        return re.sub(r'\W+', '', s).strip().lower()
    return norm(a) == norm(b)

def test_integration_transcriber_worker_real_audio():
    """
    Integration test: Use the real WhisperModel and a real audio file to check end-to-end transcription.
    """
    import time
    audio_path = 'tests/labeled_audios/sample_001.wav'
    ground_truth = "This recording should always return the same value."
    transcription_queue = multiprocessing.Queue()
    result_queue = multiprocessing.Queue()
    worker = TranscriberWorker(max_loops=1, transcription_queue=transcription_queue, result_queue=result_queue)
    try:
        transcription_queue.put(audio_path)
        worker.start()
        worker.join(timeout=60)
        last_transcription = None
        if not result_queue.empty():
            result = result_queue.get()
            last_transcription = result['text']
        print(f"Integration test transcription: {last_transcription}")
        assert last_transcription is not None, "No transcription result returned."
        assert soft_equal(last_transcription, ground_truth), f"Transcription did not match ground truth.\nExpected: {ground_truth}\nGot: {last_transcription}"
    finally:
        worker.shutdown() 