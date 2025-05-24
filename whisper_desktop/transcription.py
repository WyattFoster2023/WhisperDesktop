import asyncio
import numpy as np
from typing import Optional, Callable
from faster_whisper import WhisperModel
from .database import DatabaseManager

class TranscriptionManager:
    def __init__(self, 
                 model_name: str = "base",
                 device: str = "cpu",
                 compute_type: str = "int8",
                 db_manager: Optional[DatabaseManager] = None):
        print("\n=== DEBUG MODE: TranscriptionManager Initialized ===\n")
        self.model = None
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.db_manager = db_manager or DatabaseManager()
        self.on_transcription_callback: Optional[Callable[[str], None]] = None
        self._transcription_queue = asyncio.Queue()
        self._is_processing = False
        self._last_transcription = None
        self._load_model()
    
    def _load_model(self):
        """Load the Whisper model with error handling."""
        try:
            print(f"[DEBUG] Loading model: {self.model_name} on {self.device} with {self.compute_type}")
            self.model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type
            )
            print("[DEBUG] Model loaded successfully")
        except Exception as e:
            print(f"[ERROR] Failed to load model: {e}")
            raise RuntimeError(f"Failed to load Whisper model: {e}")
    
    def _bytes_to_numpy(self, audio_data: bytes) -> np.ndarray:
        """Convert audio bytes to numpy array."""
        try:
            # Convert bytes to numpy array of int16
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            # Convert to float32 and normalize to [-1, 1]
            audio_float = audio_array.astype(np.float32) / 32768.0
            return audio_float
        except Exception as e:
            print(f"[ERROR] Failed to convert audio data: {e}")
            raise RuntimeError(f"Failed to convert audio data: {e}")
    
    async def start_processing(self):
        print("[DEBUG] TranscriptionManager.start_processing: Started")
        if not self.model:
            self._load_model()
            
        self._is_processing = True
        while self._is_processing:
            try:
                print("[DEBUG] TranscriptionManager.start_processing: Waiting for audio data...")
                audio_data = await self._transcription_queue.get()
                print(f"[DEBUG] TranscriptionManager.start_processing: Got audio_data from queue: {type(audio_data)}, size: {len(audio_data) if audio_data else 'None'}")
                if audio_data is None:
                    print("[DEBUG] TranscriptionManager.start_processing: Received None, stopping")
                    break
                    
                # Convert audio data to numpy array
                audio_array = self._bytes_to_numpy(audio_data)
                print(f"[DEBUG] TranscriptionManager.start_processing: Converted audio data to numpy array of shape {audio_array.shape}")
                
                # Process the audio data
                print("[DEBUG] TranscriptionManager.start_processing: Starting transcription...")
                try:
                    segments, info = await asyncio.to_thread(
                        self.model.transcribe,
                        audio_array,
                        beam_size=5,
                        language="en",
                        vad_filter=True
                    )
                    
                    # Get the transcribed text
                    text = " ".join(segment.text for segment in segments).strip()
                    self._last_transcription = text
                    print(f"[DEBUG] TranscriptionManager.start_processing: Transcribed text: '{text}'")
                    
                    # Store in database
                    if self.db_manager:
                        print("[DEBUG] TranscriptionManager.start_processing: Storing in database")
                        self.db_manager.add_transcription(
                            text=text,
                            duration=info.duration if hasattr(info, 'duration') else 0.0,
                            mode="faster-whisper"
                        )
                    
                    # Call the callback if set
                    if self.on_transcription_callback:
                        print("[DEBUG] TranscriptionManager.start_processing: Calling transcription callback")
                        self.on_transcription_callback(text)
                except Exception as e:
                    print(f"[ERROR] Transcription failed: {e}")
                    if self.on_transcription_callback:
                        self.on_transcription_callback(f"Error: Transcription failed - {e}")
                    
            except Exception as e:
                print(f"[ERROR] Error processing transcription: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self._transcription_queue.task_done()
    
    async def stop_processing(self):
        """Stop the transcription processing loop."""
        self._is_processing = False
        await self._transcription_queue.put(None)
    
    async def add_audio(self, audio_data: bytes):
        print(f"[DEBUG] TranscriptionManager.add_audio: Adding audio_data of type {type(audio_data)}")
        await self._transcription_queue.put(audio_data)
    
    def get_recent_transcriptions(self, limit: int = 50):
        """Get recent transcriptions from the database."""
        if self.db_manager:
            return self.db_manager.get_recent_transcriptions(limit)
        return []
    
    async def get_transcription(self):
        """Return the last transcription result."""
        return self._last_transcription or "" 