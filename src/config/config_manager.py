import os
from typing import Any, Dict
from src.event_bus.event_bus import EventBus, EventType
import json

class ConfigurationManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigurationManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self._config_path = os.path.join(os.path.expanduser("~"), ".transcription_tool_config.json")
        self._event_bus = EventBus()
        self._default_config = {
            "transcriber": {
                "model_size": "base",
                "device": "cpu",
                "compute_type": "int8",
                "vad_filter": True,
                "vad_threshold": 2.0,
                "use_batched": False,
                "batch_size": 8
            },
            "recorder": {
                "sample_rate": 44100,
                "channels": 1,
                "default_mode": "toggle"  # or "push_to_talk"
            },
            "ui": {
                "theme": "dark",
                "always_on_top": True,
                "opacity": 0.9
            },
            "clipboard": {
                "auto_copy": True,
                "auto_paste": False
            },
            "storage": {
                "db_path": "transcriptions.db",
                "keep_audio_files": False
            }
        }
        self._config = self._default_config.copy() 

    def _deep_update(self, target, source):
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value

    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, 'r') as f:
                    loaded_config = json.load(f)
                config = self._default_config.copy()
                self._deep_update(config, loaded_config)
                return config
            except Exception as e:
                print(f"Error loading config: {e}")
                return self._default_config.copy()
        else:
            self._save_config(self._default_config)
            return self._default_config.copy()

    def _save_config(self, config: Dict[str, Any]) -> bool:
        try:
            with open(self._config_path, 'w') as f:
                json.dump(config, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def get_config(self, section: str = None, key: str = None) -> Any:
        if section is None:
            return self._config.copy()
        if section not in self._config:
            return None
        if key is None:
            return self._config[section].copy()
        if key not in self._config[section]:
            return None
        return self._config[section][key]

    def set_config(self, section: str, key: str, value: Any) -> bool:
        if section not in self._config:
            self._config[section] = {}
        if key in self._config[section] and self._config[section][key] == value:
            return True
        self._config[section][key] = value
        success = self._save_config(self._config)
        if success:
            self._event_bus.publish(EventType.CONFIG_CHANGED, {
                "section": section,
                "key": key,
                "value": value
            })
        return success

    def reset_to_defaults(self) -> bool:
        self._config = self._default_config.copy()
        success = self._save_config(self._config)
        if success:
            self._event_bus.publish(EventType.CONFIG_RESET)
        return success 