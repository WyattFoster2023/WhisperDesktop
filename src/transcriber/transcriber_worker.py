# src/transcriber/transcriber_worker.py
"""
TranscriberWorker module for background audio transcription using Faster-Whisper.
"""

import multiprocessing
from typing import Optional, Dict, Any
from src.event_bus.event_bus import EventBus, EventType
import logging
from faster_whisper import WhisperModel

logger = logging.getLogger("transcriber_worker")

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
        try:
            model = WhisperModel(
                model_size=self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            if self.use_batched and self.device != "cpu":
                from faster_whisper.transcribe import BatchedInferencePipeline
                model = BatchedInferencePipeline(model, batch_size=self.batch_size)
            logger.info(f"TranscriberWorker started with model={self.model_size}, device={self.device}, compute_type={self.compute_type}")
        except Exception as e:
            logger.error(f"Failed to initialize WhisperModel: {e}")
            return
        while not self._stop_event.is_set():
            try:
                audio_path = self._transcription_queue.get(timeout=1.0)
                if audio_path is None:
                    continue
                logger.info(f"Transcribing file: {audio_path}")
                segments, info = model.transcribe(
                    audio_path,
                    vad_filter=self.vad_filter,
                    vad_parameters={"min_silence_duration_ms": self.vad_threshold * 1000}
                )
                text = ""
                segments_data = []
                for segment in segments:
                    text += segment.text + " "
                    segments_data.append({
                        "id": segment.id,
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text
                    })
                result = {
                    "audio_path": audio_path,
                    "text": text.strip(),
                    "segments": segments_data,
                    "language": info.language,
                    "language_probability": info.language_probability
                }
                self._result_queue.put(result)
                logger.info(f"Transcription complete for: {audio_path}")
            except Exception as e:
                logger.error(f"Error in transcriber worker: {e}")

    def stop(self):
        self._stop_event.set() 