import asyncio
import numpy as np
from typing import Optional, Callable
from faster_whisper import WhisperModel
from whisper_desktop.database import DatabaseManager
import logging
import gc

class TranscriptionManager:
    def __init__(self, db_manager: DatabaseManager = None, vad_filter: bool = True, model_name: str = "base", device: str = "cpu", compute_type: str = "int8"):
        self.db_manager = db_manager or DatabaseManager()
        self.model = None
        self.vad_filter = vad_filter
        self.processing = False
        self.audio_queue = asyncio.Queue()
        self.transcription_callback = None
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self._load_model()
        
    def _load_model(self):
        """Load the Whisper model with error handling."""
        try:
            # Initialize model without VAD first
            self.model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type
            )
            
            # Configure VAD if enabled
            if self.vad_filter and hasattr(self.model, 'vad_model'):
                self.model.vad_parameters = {"min_silence_duration_ms": 500}
                
            logging.debug("Model loaded successfully")
        except Exception as e:
            logging.error(f"Failed to load model: {e}")
            raise RuntimeError(f"Failed to load Whisper model: {e}")
    
    def _bytes_to_numpy(self, audio_data):
        """Convert audio bytes to numpy array with error handling."""
        try:
            if isinstance(audio_data, bytes):
                return np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            elif isinstance(audio_data, np.ndarray):
                return audio_data
            else:
                raise ValueError(f"Unsupported audio data type: {type(audio_data)}")
        except Exception as e:
            logging.error(f"Error converting audio data: {e}")
            raise RuntimeError(f"Failed to convert audio data: {e}")
    
    async def start_processing(self):
        """Start the transcription processing loop."""
        if self.processing:
            return
            
        self.processing = True
        logging.debug("TranscriptionManager started processing")
        
        while self.processing:
            try:
                audio_data = await self.audio_queue.get()
                if audio_data is None:
                    break
                    
                # Convert audio data to numpy array if needed
                if isinstance(audio_data, bytes):
                    audio_data = self._bytes_to_numpy(audio_data)
                
                # Process audio with Whisper
                segments, _ = self.model.transcribe(audio_data)
                transcription = " ".join([segment.text for segment in segments])
                
                # Store transcription in database
                self.db_manager.add_transcription(transcription)
                
                # Call callback if set
                if self.transcription_callback:
                    self.transcription_callback(transcription)
                    
            except Exception as e:
                logging.error(f"Error in transcription processing: {e}")
                if self.transcription_callback:
                    self.transcription_callback(f"Error: {str(e)}")
                    
            finally:
                self.audio_queue.task_done()
    
    async def stop_processing(self):
        """Stop the transcription processing loop."""
        self.processing = False
        await self.audio_queue.put(None)  # Signal to stop processing
        logging.debug("TranscriptionManager stopped processing")
    
    async def add_audio(self, audio_data):
        """Add audio data to the processing queue."""
        if not self.processing:
            raise RuntimeError("TranscriptionManager is not processing")
        await self.audio_queue.put(audio_data)
    
    def set_transcription_callback(self, callback):
        """Set the callback function for transcription results."""
        self.transcription_callback = callback
    
    async def get_transcription(self):
        """Get the last transcription result."""
        return self.db_manager.get_recent_transcriptions(1)[0] if self.db_manager.get_recent_transcriptions(1) else ""
    
    def close(self):
        """Clean up resources."""
        try:
            # Stop processing if active
            if self.processing:
                asyncio.run(self.stop_processing())
            
            # Clear the model
            if self.model is not None:
                self.model = None
            
            # Force garbage collection
            gc.collect()
            
            logging.debug("TranscriptionManager resources cleaned up")
        except Exception as e:
            logging.error(f"Error during TranscriptionManager cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.close() 