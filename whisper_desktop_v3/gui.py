import sys
import asyncio
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QLabel, QPushButton, QComboBox, QCheckBox, QLineEdit,
                            QHBoxLayout, QGroupBox, QTextEdit)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QKeySequence
import pyqtgraph as pg
import pyautogui
import pyperclip
import keyboard
from .audio import AudioManager
from .transcription import TranscriptionManager
from .database import DatabaseManager
import threading
import queue
import signal
import os
from datetime import datetime
import wave

class WaveformWidget(pg.PlotWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackground('transparent')
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)
        
        # Remove axis
        self.hideAxis('left')
        self.hideAxis('bottom')
        
        # Set up plot
        self.curve = self.plot(pen=pg.mkPen(color='#2196F3', width=2))
        self.setMaximumHeight(100)
        self.setMinimumHeight(50)
        
        # Initialize data
        self.data = np.zeros(1000)
        self.ptr = 0
        
    def update(self, audio_level: float):
        """Update the waveform with new audio level."""
        self.data = np.roll(self.data, -1)
        self.data[-1] = audio_level
        self.curve.setData(self.data)

class ModernButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 20px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)

class HotkeyLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Click to set hotkey")
        self.hotkey = None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.clear()
            self.hotkey = None
            return
        
        modifiers = event.modifiers()
        key = event.key()
        
        # Convert to string representation
        key_text = QKeySequence(key).toString()
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            key_text = "Ctrl+" + key_text
        if modifiers & Qt.KeyboardModifier.AltModifier:
            key_text = "Alt+" + key_text
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            key_text = "Shift+" + key_text
        
        self.setText(key_text)
        self.hotkey = key_text
        self.clearFocus()  # Remove focus after setting hotkey

class StatusIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self.status = False
        self.setStyleSheet("""
            QWidget {
                border-radius: 6px;
                background-color: #ff4444;
            }
        """)
    
    def set_status(self, status: bool):
        self.status = status
        self.setStyleSheet(f"""
            QWidget {{
                border-radius: 6px;
                background-color: {'#44ff44' if status else '#ff4444'};
            }}
        """)

class TranscriptionGUI(QMainWindow):
    def __init__(self):
        print("\n=== DEBUG MODE: TranscriptionGUI Initialized ===\n")
        super().__init__()
        
        # Add shutdown flag first
        self._shutdown = False
        
        self.setWindowTitle("WhisperDesktop")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Initialize managers
        self.audio_manager = AudioManager()
        self.db_manager = DatabaseManager()
        self.transcription_manager = TranscriptionManager(db_manager=self.db_manager)
        
        # Set up callbacks
        self.audio_manager.on_chunk_callback = self._on_audio_chunk
        self.transcription_manager.on_transcription_callback = self._on_transcription
        
        # Create a thread-safe queue for audio data
        self.audio_queue = queue.Queue()
        
        # Start transcription processing in a background thread
        print("[DEBUG] Before starting transcription thread")
        self.transcription_thread = threading.Thread(target=self._run_transcription_loop, daemon=True)
        self.transcription_thread.start()
        print("[DEBUG] After starting transcription thread")
        print("[DEBUG] Transcription thread started")
        
        # Create central widget with rounded corners
        self.central_widget = QWidget()
        self.central_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
            }
            QGroupBox {
                border: 2px solid #2196F3;
                border-radius: 10px;
                margin-top: 1ex;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
        """)
        self.setCentralWidget(self.central_widget)
        
        # Create layout
        layout = QVBoxLayout(self.central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Status indicators layout
        status_layout = QHBoxLayout()
        
        # Model status
        model_status_layout = QHBoxLayout()
        model_status_layout.addWidget(QLabel("Model:"))
        self.model_status = StatusIndicator()
        model_status_layout.addWidget(self.model_status)
        model_status_layout.addStretch()
        status_layout.addLayout(model_status_layout)
        
        # Transcription status
        trans_status_layout = QHBoxLayout()
        trans_status_layout.addWidget(QLabel("Transcribing:"))
        self.trans_status = StatusIndicator()
        trans_status_layout.addWidget(self.trans_status)
        trans_status_layout.addStretch()
        status_layout.addLayout(trans_status_layout)
        
        layout.addLayout(status_layout)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #424242;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.status_label)
        
        # Waveform display
        self.waveform = WaveformWidget()
        layout.addWidget(self.waveform)
        
        # Output options group
        output_group = QGroupBox("Output Options")
        output_layout = QVBoxLayout()
        
        # Clipboard option
        self.clipboard_checkbox = QCheckBox("Copy to Clipboard")
        self.clipboard_checkbox.setChecked(True)
        output_layout.addWidget(self.clipboard_checkbox)
        
        # Auto-type option
        self.autotype_checkbox = QCheckBox("Auto-type at Cursor")
        self.autotype_checkbox.setChecked(True)
        output_layout.addWidget(self.autotype_checkbox)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        # Hotkeys group
        hotkeys_group = QGroupBox("Hotkeys")
        hotkeys_layout = QVBoxLayout()
        
        # PTT hotkey
        ptt_layout = QHBoxLayout()
        ptt_layout.addWidget(QLabel("PTT Hotkey:"))
        self.ptt_hotkey = HotkeyLineEdit()
        ptt_layout.addWidget(self.ptt_hotkey)
        hotkeys_layout.addLayout(ptt_layout)
        
        # Toggle hotkey
        toggle_layout = QHBoxLayout()
        toggle_layout.addWidget(QLabel("Toggle Hotkey:"))
        self.toggle_hotkey = HotkeyLineEdit()
        toggle_layout.addWidget(self.toggle_hotkey)
        hotkeys_layout.addLayout(toggle_layout)
        
        hotkeys_group.setLayout(hotkeys_layout)
        layout.addWidget(hotkeys_group)
        
        # Mode selector
        self.mode_selector = QComboBox()
        self.mode_selector.addItems(["PTT", "Toggle"])
        self.mode_selector.setStyleSheet("""
            QComboBox {
                background-color: white;
                border: 2px solid #2196F3;
                border-radius: 10px;
                padding: 5px 10px;
                font-size: 14px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
            }
        """)
        layout.addWidget(self.mode_selector)
        
        # PTT mode button
        self.ptt_button = ModernButton("Hold to Record (PTT Mode)")
        self.ptt_button.pressed.connect(self.start_recording)
        self.ptt_button.released.connect(self.stop_recording)
        layout.addWidget(self.ptt_button)
        
        # Toggle mode button
        self.toggle_button = ModernButton("Start Recording (Toggle Mode)")
        self.toggle_button.clicked.connect(self.toggle_recording)
        layout.addWidget(self.toggle_button)
        
        # Add transcription log
        self.transcription_log = QTextEdit()
        self.transcription_log.setReadOnly(True)
        self.transcription_log.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 2px solid #2196F3;
                border-radius: 10px;
                padding: 5px;
                font-size: 14px;
            }
        """)
        self.transcription_log.setMaximumHeight(100)
        layout.addWidget(self.transcription_log)
        
        # Set up update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_waveform)
        self.timer.start(50)  # Update every 50ms
        
        # Set window size and position
        self.setFixedSize(400, 500)  # Increased height for new controls
        self.move(100, 100)
        
        # For dragging the window
        self.oldPos = None
        
        # Set up hotkey handlers
        self.ptt_hotkey.textChanged.connect(self._update_ptt_hotkey)
        self.toggle_hotkey.textChanged.connect(self._update_toggle_hotkey)
        
        # Initialize hotkeys
        self.ptt_hotkey.setText("Ctrl+Shift+R")  # Default PTT hotkey
        self.toggle_hotkey.setText("Ctrl+Shift+T")  # Default toggle hotkey
        
        # Set up signal handlers for graceful shutdown
        if os.name != 'nt':  # Not Windows
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.oldPos = event.globalPosition().toPoint()
    
    def mouseMoveEvent(self, event):
        if self.oldPos:
            delta = event.globalPosition().toPoint() - self.oldPos
            self.move(self.pos() + delta)
            self.oldPos = event.globalPosition().toPoint()
    
    def mouseReleaseEvent(self, event):
        self.oldPos = None
    
    def _on_audio_chunk(self, chunk):
        # Use chunk.data and chunk.timestamp for debug and waveform
        try:
            print(f"[DEBUG] _on_audio_chunk: Received chunk with {len(chunk.data)} bytes at {getattr(chunk, 'timestamp', 'N/A')}")
            audio_level = self.audio_manager.get_audio_level(chunk.data)
            self.waveform.update(audio_level)
        except Exception as e:
            print(f"[ERROR] in _on_audio_chunk: {e}")
    
    def _on_transcription(self, text: str):
        """Handle completed transcription."""
        self.trans_status.set_status(False)
        if self.clipboard_checkbox.isChecked():
            pyperclip.copy(text)
        if self.autotype_checkbox.isChecked():
            pyautogui.write(text)
        self.status_label.setText("Transcription complete")
        self.transcription_log.append(text)
    
    def start_recording(self):
        """Start recording in PTT mode."""
        self.audio_manager.start_recording()
        self.status_label.setText("Recording...")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #F44336;
                font-size: 16px;
                font-weight: bold;
            }
        """)
    
    def stop_recording(self):
        print("[DEBUG] stop_recording: Called")
        audio_data = self.audio_manager.stop_recording()
        print(f"[DEBUG] stop_recording: Got {len(audio_data)} bytes of audio data")
        
        if audio_data:
            # Save audio to file
            # Create recordings directory if it doesn't exist
            os.makedirs("recordings", exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recordings/recording_{timestamp}.wav"
            
            # Save as WAV file
            with wave.open(filename, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
                wav_file.setframerate(16000)  # 16kHz
                wav_file.writeframes(audio_data)
            
            print(f"[DEBUG] stop_recording: Saved audio to {filename}")
            
            # Put audio data on queue for transcription
            self.audio_queue.put(audio_data)
            print("[DEBUG] stop_recording: Audio data put on queue")
            
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #424242;
                font-size: 16px;
                font-weight: bold;
            }
        """)
    
    def toggle_recording(self):
        """Toggle recording state."""
        if self.audio_manager.recording:
            self.stop_recording()
        else:
            self.start_recording()
    
    def closeEvent(self, event):
        """Clean up when closing the window."""
        print("Cleaning up resources...")
        self._shutdown = True
        
        # Remove hotkeys
        if self.ptt_hotkey.hotkey:
            try:
                keyboard.remove_hotkey(self.ptt_hotkey.hotkey)
            except:
                pass
        if self.toggle_hotkey.hotkey:
            try:
                keyboard.remove_hotkey(self.toggle_hotkey.hotkey)
            except:
                pass
        
        self.audio_queue.put(None)  # Signal the background thread to exit
        self.audio_manager.cleanup()
        event.accept()

    def update_waveform(self):
        # If recording, update the waveform with the last chunk's audio level
        if self.audio_manager.recording and self.audio_manager.chunks:
            audio_level = self.audio_manager.get_audio_level(self.audio_manager.chunks[-1].data)
            self.waveform.update(audio_level)
        else:
            # Slowly decay the waveform to zero when not recording
            self.waveform.update(0.0)

    def _run_transcription_loop(self):
        print("[DEBUG] Entered _run_transcription_loop thread")
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def process_audio_queue():
            print("\n=== DEBUG MODE: Starting Transcription Loop ===\n")
            while not self._shutdown:
                try:
                    print("[DEBUG] Waiting for audio data from queue...")
                    # Get audio data from GUI queue
                    audio_data = await asyncio.get_event_loop().run_in_executor(
                        None, self.audio_queue.get
                    )
                    if audio_data is None:
                        print("[DEBUG] Received None from queue, breaking loop")
                        break
                    
                    print(f"[DEBUG] _run_transcription_loop: Got audio data from queue: {len(audio_data)} bytes")
                    # Forward to transcription manager
                    await self.transcription_manager.add_audio(audio_data)
                    print("[DEBUG] Audio data forwarded to transcription manager")
                except Exception as e:
                    print(f"[ERROR] in process_audio_queue: {e}")
                    import traceback
                    traceback.print_exc()
        
        async def run_all():
            print("[DEBUG] Starting transcription manager and audio queue processor")
            # Run both the transcription manager and audio queue processor concurrently
            await asyncio.gather(
                self.transcription_manager.start_processing(),
                process_audio_queue()
            )
        
        try:
            # Run both coroutines concurrently
            loop.run_until_complete(run_all())
        except Exception as e:
            print(f"[ERROR] in run_all: {e}")
            import traceback
            traceback.print_exc()
        finally:
            loop.close()

    async def _transcription_worker(self):
        """Worker function for transcription processing."""
        try:
            self.model_status.set_status(False)  # Model is loading
            await self.transcription_manager.start_processing()
            self.model_status.set_status(True)  # Model is ready
        except Exception as e:
            print(f"Error in transcription worker: {e}")
            self.model_status.set_status(False)

    def _update_ptt_hotkey(self, hotkey):
        """Update the PTT hotkey."""
        if self.ptt_hotkey.hotkey:
            try:
                keyboard.remove_hotkey(self.ptt_hotkey.hotkey)
            except:
                pass
            keyboard.add_hotkey(self.ptt_hotkey.hotkey, self.start_recording, trigger_on_release=False)
            keyboard.add_hotkey(self.ptt_hotkey.hotkey, self.stop_recording, trigger_on_release=True)
    
    def _update_toggle_hotkey(self, hotkey):
        """Update the toggle hotkey."""
        if self.toggle_hotkey.hotkey:
            try:
                keyboard.remove_hotkey(self.toggle_hotkey.hotkey)
            except:
                pass
            keyboard.add_hotkey(self.toggle_hotkey.hotkey, self.toggle_recording)

    def _signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown."""
        print("\nShutting down gracefully...")
        self._shutdown = True
        self.close()
        QApplication.quit()

def run_gui():
    app = QApplication(sys.argv)
    window = TranscriptionGUI()
    window.show()
    
    # Set up periodic check for keyboard interrupt
    def check_interrupt():
        if window._shutdown:
            app.quit()
            return
        
        try:
            # Check if Ctrl+C was pressed
            if keyboard.is_pressed('ctrl+c'):
                print("\nShutting down gracefully...")
                window.close()
                app.quit()
        except:
            pass
    
    timer = QTimer()
    timer.timeout.connect(check_interrupt)
    timer.start(100)  # Check every 100ms
    
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        window.close()
        app.quit() 