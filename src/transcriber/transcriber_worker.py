# src/transcriber/transcriber_worker.py
"""
TranscriberWorker module for background audio transcription using Faster-Whisper.
"""

import multiprocessing
from typing import Optional, Dict, Any
from src.event_bus.event_bus import EventBus, EventType

class TranscriberWorker(multiprocessing.Process):
    """Background worker for audio transcription."""
    def __init__(self, model_size="base", device="cpu", compute_type="int8", 
                 vad_filter=True, vad_threshold=2.0, use_batched=False, batch_size=8):
        super().__init__()
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.vad_filter = vad_filter
        self.vad_threshold = vad_threshold
        self.use_batched = use_batched
        self.batch_size = batch_size
        self.daemon = True
        self._stop_event = multiprocessing.Event()
        self._event_bus = EventBus()
        self._transcription_queue = self._event_bus.get_queue('transcription')
        self._result_queue = self._event_bus.get_queue('result')

    def run(self):
        pass

    def stop(self):
        self._stop_event.set() 