from src.event_bus.event_bus import EventBus, EventType
import pyperclip
import pyautogui

class ClipboardController:
    """
    Handles clipboard operations and optional paste simulation.
    """
    def __init__(self, auto_copy=True, auto_paste=False):
        self.auto_copy = auto_copy
        self.auto_paste = auto_paste
        self.event_bus = EventBus()
        self._setup_event_handlers()

    def _setup_event_handlers(self):
        self.event_bus.subscribe(EventType.TRANSCRIPTION_COMPLETED, self._on_transcription_completed)

    def _on_transcription_completed(self, data):
        if self.auto_copy and "text" in data:
            self.copy_to_clipboard(data["text"])
            if self.auto_paste:
                self.simulate_paste()

    def copy_to_clipboard(self, text):
        try:
            pyperclip.copy(text)
            self.event_bus.publish(EventType.TEXT_COPIED_TO_CLIPBOARD, {"text": text})
            return True
        except Exception as e:
            print(f"Error copying to clipboard: {e}")
            return False

    def simulate_paste(self):
        try:
            pyautogui.hotkey('ctrl', 'v')
            self.event_bus.publish(EventType.PASTE_SIMULATED)
            return True
        except Exception as e:
            print(f"Error simulating paste: {e}")
            return False

    def set_auto_copy(self, enabled: bool):
        self.auto_copy = enabled

    def set_auto_paste(self, enabled: bool):
        self.auto_paste = enabled 