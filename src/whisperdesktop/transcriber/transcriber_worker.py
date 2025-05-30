# src/transcriber/transcriber_worker.py
"""
TranscriberWorker module for background audio transcription using Faster-Whisper.
"""

import multiprocessing
from typing import Optional, Dict, Any
from whisperdesktop.event_bus.event_bus import EventBus, EventType
from whisperdesktop.utils.logger import Logger
from faster_whisper import WhisperModel

logger = Logger("transcriber_worker")

class TranscriberWorker(multiprocessing.Process):
    """Background worker for audio transcription."""
    def __init__(self, model_size="tiny", device="cpu", compute_type="int8", 
                 vad_filter=True, vad_threshold=2.0, use_batched=False, batch_size=8, max_loops=None,
                 event_bus=None, transcription_queue=None, result_queue=None):
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
        self._max_loops = max_loops
        self._event_bus = event_bus
        self._transcription_queue = transcription_queue
        self._result_queue = result_queue

    def run(self):
        event_bus = self._event_bus if self._event_bus is not None else EventBus()
        transcription_queue = self._transcription_queue if self._transcription_queue is not None else event_bus.get_queue('transcription')
        result_queue = self._result_queue if self._result_queue is not None else event_bus.get_queue('result')
        try:
            model = WhisperModel(
                self.model_size,
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
        loop_count = 0
        while not self._stop_event.is_set():
            if self._max_loops is not None and loop_count >= self._max_loops:
                break
            loop_count += 1
            try:
                audio_path = transcription_queue.get(timeout=1.0)
                if audio_path is None:
                    continue
                logger.info(f"Transcribing file: {audio_path}")
                event_bus.publish(EventType.TRANSCRIPTION_REQUESTED, audio_path)
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
                result_queue.put(result)
                logger.info(f"Transcription complete for: {audio_path}")
                event_bus.publish(EventType.TRANSCRIPTION_COMPLETED, result)
            except Exception as e:
                logger.error(f"Error in transcriber worker: {e}")

    def stop(self):
        self._stop_event.set()

    def shutdown(self, timeout=5):
        """Signal the worker to stop and join the process."""
        self._stop_event.set()
        if self.is_alive():
            self.join(timeout=timeout)
            if self.is_alive():
                # If still alive, terminate (force kill)
                self.terminate()
                self.join(timeout=timeout)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown() 