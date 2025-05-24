import json
import os
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class Settings:
    # Model settings
    model_name: str = "base"
    device: str = "cpu"
    compute_type: str = "int8"
    
    # Shortcut settings
    start_recording_shortcut: str = "Ctrl+Shift+R"
    stop_recording_shortcut: str = "Ctrl+Shift+S"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "device": self.device,
            "compute_type": self.compute_type,
            "start_recording_shortcut": self.start_recording_shortcut,
            "stop_recording_shortcut": self.stop_recording_shortcut
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Settings':
        return cls(**data)

class SettingsManager:
    def __init__(self, settings_file: str = "settings.json"):
        self.settings_file = settings_file
        self.settings = self.load_settings()
    
    def load_settings(self) -> Settings:
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                return Settings.from_dict(data)
            except Exception as e:
                print(f"Error loading settings: {e}")
        return Settings()
    
    def save_settings(self, settings: Settings):
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings.to_dict(), f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def update_settings(self, **kwargs):
        current_dict = self.settings.to_dict()
        current_dict.update(kwargs)
        self.settings = Settings.from_dict(current_dict)
        self.save_settings(self.settings) 