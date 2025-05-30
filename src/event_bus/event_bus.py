# src/event_bus/event_bus.py

"""
EventBus module for inter-module communication using the Singleton pattern.
"""

from enum import Enum
from multiprocessing import Queue
from typing import Callable, Dict, List, Any
import threading

class EventType(Enum):
    RECORDING_STARTED = 1
    RECORDING_STOPPED = 2
    TRANSCRIPTION_REQUESTED = 3
    TRANSCRIPTION_COMPLETED = 4
    # Add more event types as needed

class ResultQueue(Queue):
    """Specialized queue for handling transcription results."""
    pass

class EventBus:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EventBus, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance

    def _initialize(self):
        self._subscribers: Dict[EventType, List[Callable[[Any], None]]] = {event_type: [] for event_type in EventType}
        self._queues: Dict[str, Queue] = {}
        self._queues['transcription'] = Queue()
        self._queues['result'] = Queue()
        self._event_lock = threading.Lock()

    def get_queue(self, name: str) -> Queue:
        return self._queues.get(name)

    def publish(self, event_type: EventType, payload: Any = None):
        with self._event_lock:
            for callback in self._subscribers[event_type]:
                callback(payload)

    def subscribe(self, event_type: EventType, callback: Callable[[Any], None]):
        with self._event_lock:
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable[[Any], None]):
        with self._event_lock:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)

    def add_queue(self, name: str):
        with self._event_lock:
            if name not in self._queues:
                self._queues[name] = Queue()

    def add_result_queue(self, name: str):
        with self._event_lock:
            if name not in self._queues:
                self._queues[name] = ResultQueue()

# Implementation will follow in subsequent subtasks. 