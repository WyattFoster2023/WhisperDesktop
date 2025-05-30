from whisperdesktop.event_bus.event_bus import EventBus
from whisperdesktop.recorder.recorder import Recorder
from whisperdesktop.storage.storage_manager import StorageManager
from whisperdesktop.clipboard.clipboard_controller import ClipboardController
from whisperdesktop.transcriber.transcriber_worker import TranscriberWorker
from PyQt5.QtWidgets import QApplication
from whisperdesktop.ui.ui_controller import UIController
from whisperdesktop.utils.logger import Logger

class ApplicationController:
    def __init__(self):
        # Initialize EventBus first (singleton)
        self._event_bus = EventBus()
        # Initialize core modules
        self._recorder = Recorder()
        self._storage_manager = StorageManager()
        self._clipboard_controller = ClipboardController(auto_copy=True, auto_paste=False)
        # TranscriberWorker integration
        transcription_queue = self._event_bus.get_queue('transcription')
        result_queue = self._event_bus.get_queue('result')
        self._transcriber_worker = TranscriberWorker(
            model_size="base",
            device="cpu",
            compute_type="int8",
            vad_filter=True,
            vad_threshold=2.0,
            event_bus=self._event_bus,
            transcription_queue=transcription_queue,
            result_queue=result_queue
        )
        self._transcriber_worker.start()
        self._result_queue = result_queue
        # UI integration
        self._app = QApplication([])
        self._ui_controller = UIController(event_bus=self._event_bus)
        # Placeholders for future integration
        self._setup_event_handlers()

    def _setup_event_handlers(self):
        # Subscribe to core recording events
        from whisperdesktop.event_bus.event_bus import EventType
        self._event_bus.subscribe(EventType.START_RECORDING_REQUESTED, self._on_start_recording_requested)
        self._event_bus.subscribe(EventType.STOP_RECORDING_REQUESTED, self._on_stop_recording_requested)
        self._event_bus.subscribe(EventType.TOGGLE_RECORDING_REQUESTED, self._on_toggle_recording_requested)

    def _on_start_recording_requested(self, data):
        try:
            self._recorder.start_recording()
        except Exception as e:
            Logger().error(f"Error in start_recording: {e}")

    def _on_stop_recording_requested(self, data):
        try:
            self._recorder.stop_recording()
        except Exception as e:
            Logger().error(f"Error in stop_recording: {e}")

    def _on_toggle_recording_requested(self, data):
        try:
            self._recorder.toggle_recording()
        except Exception as e:
            Logger().error(f"Error in toggle_recording: {e}")

    def _check_result_queue(self):
        # Poll the result queue for new transcription results (non-blocking)
        try:
            while self._result_queue is not None and not self._result_queue.empty():
                result = self._result_queue.get_nowait()
                if result:
                    # Save transcription to database
                    transcription_id = self._storage_manager.save_transcription(
                        text=result.get("text", ""),
                        segments_metadata=result.get("segments", []),
                        audio_path=result.get("audio_path")
                    )
                    # Delete audio file after successful save
                    audio_path = result.get("audio_path")
                    if transcription_id and audio_path:
                        import os
                        try:
                            os.remove(audio_path)
                        except Exception as e:
                            Logger().error(f"Error deleting audio file {audio_path}: {e}")
                    # Publish transcription completed event
                    from whisperdesktop.event_bus.event_bus import EventType
                    self._event_bus.publish(EventType.TRANSCRIPTION_COMPLETED, {
                        "id": transcription_id,
                        "text": result.get("text", ""),
                        "segments": result.get("segments", [])
                    })
        except Exception as e:
            Logger().error(f"Error processing result queue: {e}")

    def run(self):
        # Show the UI and start the Qt event loop
        try:
            self._ui_controller.show()
            return self._app.exec_()
        except Exception as e:
            Logger().error(f"Error in application run loop: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        # Properly release/terminate all resources
        try:
            if hasattr(self, '_transcriber_worker') and self._transcriber_worker:
                if self._transcriber_worker.is_alive():
                    self._transcriber_worker.stop()
                    self._transcriber_worker.join(timeout=1.0)
            if hasattr(self, '_recorder') and self._recorder:
                self._recorder.cleanup()
            # Add additional cleanup for other modules as needed
        except Exception as e:
            Logger().error(f"Error during cleanup: {e}") 