from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QDialog, QTextEdit, QApplication, QComboBox
from PyQt5.QtCore import Qt, QSize, QTimer
from enum import Enum
from src.event_bus.event_bus import EventBus, EventType
from src.storage.storage_manager import StorageManager
from src.utils.logger import Logger

class UIStatus(Enum):
    IDLE = "Ready"
    RECORDING = "Recording..."
    TRANSCRIBING = "Transcribing..."
    SAVED = "Saved!"

class UIController(QMainWindow):
    def __init__(self, event_bus=None):
        super().__init__()
        self._event_bus = event_bus if event_bus is not None else EventBus()
        self._storage_manager = StorageManager()
        self._history_data = []
        # Set window properties
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle('Transcription Tool')
        self.resize(300, 100)
        # Create central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self._setup_ui()
        self._setup_event_handlers()
        # Status management
        self.current_status = UIStatus.IDLE
        self._update_status()
        # History refresh timer
        self._history_timer = QTimer(self)
        self._history_timer.timeout.connect(self._refresh_history)
        self._history_timer.start(10000)  # 10 seconds
        self._refresh_history()

    def _setup_ui(self):
        # Button layout
        button_layout = QHBoxLayout()
        # Record button
        self.record_button = QPushButton('Record')
        self.record_button.setCheckable(True)
        self.record_button.setFixedSize(QSize(80, 30))
        button_layout.addWidget(self.record_button)
        # Push-to-talk button
        self.ptt_button = QPushButton('Push to Talk')
        self.ptt_button.setFixedSize(QSize(100, 30))
        button_layout.addWidget(self.ptt_button)
        self.main_layout.addLayout(button_layout)
        # History dropdown layout
        history_layout = QHBoxLayout()
        history_label = QLabel('History:')
        history_label.setStyleSheet('color: white;')
        history_layout.addWidget(history_label)
        self.history_dropdown = QComboBox()
        self.history_dropdown.setFixedWidth(200)
        self.history_dropdown.activated.connect(self._on_history_item_selected)
        history_layout.addWidget(self.history_dropdown)
        self.main_layout.addLayout(history_layout)
        # Status label
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.status_label)
        # Style
        self.setStyleSheet('''
            QMainWindow {
                background-color: rgba(40, 40, 40, 180);
                border-radius: 10px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
            }
            QPushButton:checked {
                background-color: #F44336;
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
        ''')
        # Connect signals to handlers
        self.record_button.clicked.connect(self._on_record_clicked)
        self.ptt_button.pressed.connect(self._on_ptt_pressed)
        self.ptt_button.released.connect(self._on_ptt_released)

    def _setup_event_handlers(self):
        self._event_bus.subscribe(EventType.RECORDING_STARTED, self._on_recording_started)
        self._event_bus.subscribe(EventType.RECORDING_STOPPED, self._on_recording_stopped)
        self._event_bus.subscribe(EventType.TRANSCRIPTION_REQUESTED, self._on_transcription_requested)
        self._event_bus.subscribe(EventType.TRANSCRIPTION_COMPLETED, self._on_transcription_completed)

    def _on_recording_started(self, data):
        self.current_status = UIStatus.RECORDING
        self.record_button.setChecked(True)
        self._update_status()

    def _on_recording_stopped(self, data):
        self.current_status = UIStatus.TRANSCRIBING
        self.record_button.setChecked(False)
        self._update_status()
        QTimer.singleShot(1000, self.reset_status)

    def _on_transcription_requested(self, data):
        self.current_status = UIStatus.TRANSCRIBING
        self._update_status()

    def _on_transcription_completed(self, data):
        self.set_status_saved()

    def _on_record_clicked(self):
        if self.record_button.isChecked():
            self._event_bus.publish(EventType.TOGGLE_RECORDING_REQUESTED)
        else:
            self._event_bus.publish(EventType.STOP_RECORDING_REQUESTED)

    def _on_ptt_pressed(self):
        self._event_bus.publish(EventType.START_RECORDING_REQUESTED)

    def _on_ptt_released(self):
        self._event_bus.publish(EventType.STOP_RECORDING_REQUESTED)

    def _on_history_item_selected(self, index):
        pass  # To be implemented in next subtask

    def _update_status(self):
        self.status_label.setText(self.current_status.value)

    def set_status_saved(self):
        self.current_status = UIStatus.SAVED
        self._update_status()
        QTimer.singleShot(3000, self.reset_status)

    def reset_status(self):
        self.current_status = UIStatus.IDLE
        self._update_status()

    def _refresh_history(self):
        try:
            transcriptions = self._storage_manager.get_recent_transcriptions(limit=10)
        except Exception as e:
            Logger().error(f"Failed to refresh history: {e}")
            transcriptions = []
        self.history_dropdown.clear()
        self._history_data = transcriptions
        if not transcriptions:
            self.history_dropdown.addItem("No transcription history")
            return
        for transcription in transcriptions:
            timestamp = transcription.get('timestamp', '')
            text = transcription.get('text', '')
            preview_words = text.split()[:15]
            preview = ' '.join(preview_words)
            if len(text.split()) > 15:
                preview += '...'
            entry = f"{timestamp} - {preview}"
            self.history_dropdown.addItem(entry)

class TranscriptionHistoryDialog(QDialog):
    def __init__(self, transcription, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Transcription Details")
        self.setModal(True)
        self.setFixedSize(500, 300)
        layout = QVBoxLayout(self)
        # Text display
        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setText(transcription["text"])
        layout.addWidget(self._text_edit)
        # Copy button
        copy_button = QPushButton("Copy to Clipboard")
        copy_button.clicked.connect(lambda: self._copy_to_clipboard(transcription["text"]))
        layout.addWidget(copy_button)

    def _copy_to_clipboard(self, text):
        clipboard = QApplication.clipboard()
        clipboard.setText(text) 