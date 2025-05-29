import sys
import asyncio
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QLabel, QPushButton, QComboBox, QCheckBox, QLineEdit,
                            QHBoxLayout, QGroupBox, QTextEdit)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QKeySequence, QShortcut
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
from .settings import SettingsManager
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

class AsyncWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(Exception)
    
    def __init__(self, coro):
        super().__init__()
        self.coro = coro
        self.loop = None
        print(f"[DEBUG] AsyncWorker initialized with coroutine: {coro.__name__ if hasattr(coro, '__name__') else type(coro)}")
    
    def run(self):
        try:
            print("[DEBUG] AsyncWorker starting execution")
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            result = self.loop.run_until_complete(self.coro)
            print("[DEBUG] AsyncWorker completed successfully")
            self.finished.emit(result)
        except Exception as e:
            print(f"[ERROR] AsyncWorker failed: {e}")
            self.error.emit(e)
        finally:
            if self.loop:
                print("[DEBUG] AsyncWorker cleaning up event loop")
                self.loop.close()

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
        self.settings_manager = SettingsManager()
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
        # Initialize status indicators before init_ui
        self.model_status = StatusIndicator()
        self.trans_status = StatusIndicator()
        # Initialize UI components
        self.init_ui()
        
        # Initialize audio and transcription after UI
        self.init_audio()
        self.init_transcription()
        
        # Set up update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_waveform)
        self.timer.start(50)  # Update every 50ms
        
        # Set window size and position
        self.setFixedSize(400, 500)
        self.move(100, 100)
        
        # For dragging the window
        self.oldPos = None
        
        # Set up signal handlers for graceful shutdown
        if os.name != 'nt':  # Not Windows
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
    
    def init_ui(self):
        # Settings group
        settings_group = QGroupBox("Settings")
        settings_layout = QVBoxLayout()
        
        # Model settings
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large-v3"])
        self.model_combo.setCurrentText(self.settings_manager.settings.model_name)
        model_layout.addWidget(self.model_combo)
        
        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("Device:"))
        self.device_combo = QComboBox()
        self.device_combo.addItems(["cpu", "cuda"])
        self.device_combo.setCurrentText(self.settings_manager.settings.device)
        device_layout.addWidget(self.device_combo)
        
        compute_layout = QHBoxLayout()
        compute_layout.addWidget(QLabel("Compute Type:"))
        self.compute_combo = QComboBox()
        self.compute_combo.addItems(["int8", "float16"])
        self.compute_combo.setCurrentText(self.settings_manager.settings.compute_type)
        compute_layout.addWidget(self.compute_combo)
        
        settings_layout.addLayout(model_layout)
        settings_layout.addLayout(device_layout)
        settings_layout.addLayout(compute_layout)
        
        # Shortcut settings
        shortcut_layout = QHBoxLayout()
        shortcut_layout.addWidget(QLabel("Start Recording:"))
        self.start_shortcut = QLineEdit(self.settings_manager.settings.start_recording_shortcut)
        shortcut_layout.addWidget(self.start_shortcut)
        
        shortcut_layout2 = QHBoxLayout()
        shortcut_layout2.addWidget(QLabel("Stop Recording:"))
        self.stop_shortcut = QLineEdit(self.settings_manager.settings.stop_recording_shortcut)
        shortcut_layout2.addWidget(self.stop_shortcut)
        
        settings_layout.addLayout(shortcut_layout)
        settings_layout.addLayout(shortcut_layout2)
        
        # Save settings button
        save_settings_btn = QPushButton("Save Settings")
        save_settings_btn.clicked.connect(self.save_settings)
        settings_layout.addWidget(save_settings_btn)
        
        settings_group.setLayout(settings_layout)
        self.central_widget.layout().addWidget(settings_group)
        
        # Waveform display
        self.waveform = WaveformWidget()
        self.central_widget.layout().addWidget(self.waveform)
        
        # Recording controls
        self.record_button = QPushButton("Start Recording (Ctrl+Shift+R)")
        self.record_button.clicked.connect(self.toggle_recording)
        self.central_widget.layout().addWidget(self.record_button)
        
        # Transcription output
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.central_widget.layout().addWidget(self.output)
        
        # Add status indicators to the UI for test compatibility
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("Model Status:"))
        status_layout.addWidget(self.model_status)
        status_layout.addWidget(QLabel("Transcription Status:"))
        status_layout.addWidget(self.trans_status)
        self.central_widget.layout().addLayout(status_layout)
        
        # Set up shortcuts
        self.update_shortcuts()
    
    def update_shortcuts(self):
        # Remove existing shortcuts
        for shortcut in self.findChildren(QShortcut):
            shortcut.deleteLater()
        
        # Add new shortcuts
        start_shortcut = QShortcut(QKeySequence(self.settings_manager.settings.start_recording_shortcut), self)
        start_shortcut.activated.connect(self.start_recording)
        
        stop_shortcut = QShortcut(QKeySequence(self.settings_manager.settings.stop_recording_shortcut), self)
        stop_shortcut.activated.connect(self.stop_recording)
        
        # Update button text
        self.record_button.setText(f"Start Recording ({self.settings_manager.settings.start_recording_shortcut})")
    
    def save_settings(self):
        # If CPU and float16, force int8
        device = self.device_combo.currentText()
        compute_type = self.compute_combo.currentText()
        if device == "cpu" and compute_type == "float16":
            compute_type = "int8"
            self.output.append("[Warning] float16 is not supported on CPU. Using int8 instead.")
            self.compute_combo.setCurrentText("int8")
        self.settings_manager.update_settings(
            model_name=self.model_combo.currentText(),
            device=device,
            compute_type=compute_type,
            start_recording_shortcut=self.start_shortcut.text(),
            stop_recording_shortcut=self.stop_shortcut.text()
        )
        self.update_shortcuts()
        # Reinitialize transcription manager with new settings
        self.init_transcription()
    
    def init_audio(self):
        self.audio_manager = AudioManager()
        self.audio_manager.on_chunk_callback = self.on_audio_chunk
    
    def init_transcription(self):
        try:
            print("[DEBUG] Initializing transcription manager")
            device = self.settings_manager.settings.device
            compute_type = self.settings_manager.settings.compute_type
            if device == "cpu" and compute_type == "float16":
                compute_type = "int8"
                self.output.append("[Warning] float16 is not supported on CPU. Using int8 instead.")
                self.settings_manager.update_settings(compute_type="int8")
            self.transcription_manager = TranscriptionManager(
                model_name=self.settings_manager.settings.model_name,
                device=device,
                compute_type=compute_type
            )
            print("[DEBUG] Transcription manager initialized")
            self.transcription_manager.on_transcription_callback = self.on_transcription
            # Start transcription processing in a separate thread
            print("[DEBUG] Creating transcription worker")
            self.transcription_worker = AsyncWorker(self.transcription_manager.start_processing())
            self.transcription_worker.error.connect(self.handle_transcription_error)
            print("[DEBUG] Starting transcription worker")
            self.transcription_worker.start()
            print("[DEBUG] Transcription worker started")
        except Exception as e:
            print(f"[ERROR] Failed to initialize transcription: {e}")
            self.output.append(f"Error: Failed to initialize transcription: {e}")
    
    def handle_transcription_error(self, error):
        print(f"Transcription error: {error}")
        self.output.append(f"Error: {error}")
    
    def toggle_recording(self):
        if self.audio_manager.recording:
            self.stop_recording()
        else:
            self.start_recording()
    
    def start_recording(self):
        if not self.audio_manager.recording:
            try:
                self.audio_manager.start_recording()
                self.record_button.setText(f"Stop Recording ({self.settings_manager.settings.stop_recording_shortcut})")
            except Exception as e:
                print(f"Error starting recording: {e}")
                self.output.append(f"Error: Failed to start recording: {e}")
    
    def stop_recording(self):
        if self.audio_manager.recording:
            try:
                audio_data = self.audio_manager.stop_recording()
                self.record_button.setText(f"Start Recording ({self.settings_manager.settings.start_recording_shortcut})")
                if audio_data:
                    # Store worker as instance variable to prevent garbage collection
                    self.audio_worker = AsyncWorker(self.transcription_manager.add_audio(audio_data))
                    self.audio_worker.error.connect(self.handle_transcription_error)
                    self.audio_worker.finished.connect(self._on_audio_worker_finished)
                    self.audio_worker.start()
            except Exception as e:
                print(f"Error stopping recording: {e}")
                self.output.append(f"Error: Failed to stop recording: {e}")
    
    def _on_audio_worker_finished(self):
        """Clean up the audio worker after it's done."""
        if hasattr(self, 'audio_worker'):
            self.audio_worker.deleteLater()
            delattr(self, 'audio_worker')
    
    def on_audio_chunk(self, chunk):
        try:
            audio_level = self.audio_manager.get_audio_level(chunk.data)
            # Use QTimer.singleShot to ensure UI updates happen in the main thread
            QTimer.singleShot(0, lambda: self.waveform.update(audio_level))
        except Exception as e:
            print(f"Error updating waveform: {e}")
    
    def on_transcription(self, text):
        # Use QTimer.singleShot to ensure UI updates happen in the main thread
        QTimer.singleShot(0, lambda: self.output.append(text))
    
    def update_waveform(self):
        if hasattr(self, 'waveform'):
            try:
                if self.audio_manager.recording and self.audio_manager.chunks:
                    audio_level = self.audio_manager.get_audio_level(self.audio_manager.chunks[-1].data)
                    self.waveform.update(audio_level)
                else:
                    self.waveform.update(0.0)
            except Exception as e:
                print(f"Error updating waveform: {e}")
    
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
    
    def closeEvent(self, event):
        """Clean up when closing the window."""
        print("Cleaning up resources...")
        self._shutdown = True
        
        # Stop the async timer
        if hasattr(self, 'async_timer'):
            self.async_timer.stop()
        
        # Clean up audio resources
        try:
            self.audio_manager.cleanup()
        except Exception as e:
            print(f"Error cleaning up audio: {e}")
        
        # Clean up transcription worker and manager
        if hasattr(self, 'transcription_worker'):
            try:
                # Stop the transcription processing
                asyncio.run(self.transcription_manager.stop_processing())
                # Wait for the worker to finish
                self.transcription_worker.quit()
                self.transcription_worker.wait(1000)  # Wait up to 1 second
                if self.transcription_worker.isRunning():
                    print("Warning: Transcription worker did not stop gracefully")
                    self.transcription_worker.terminate()  # Force stop if needed
            except Exception as e:
                print(f"Error cleaning up transcription worker: {e}")
        if hasattr(self, 'transcription_manager'):
            try:
                self.transcription_manager.close()
            except Exception as e:
                print(f"Error closing transcription manager: {e}")
        event.accept()
    
    def _signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown."""
        print("\nShutting down gracefully...")
        self._shutdown = True
        self.close()
        QApplication.quit()

    @property
    def is_recording(self):
        return getattr(self.audio_manager, 'recording', False)

    @property
    def transcription_text(self):
        return self.output

    @property
    def settings(self):
        return self.settings_manager.settings

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