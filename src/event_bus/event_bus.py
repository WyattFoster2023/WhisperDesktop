# src/event_bus/event_bus.py

"""
EventBus module for inter-module communication using the Singleton pattern.
"""

from enum import Enum
from multiprocessing import Queue
from typing import Callable, Dict, List, Any
import threading
import logging

logger = logging.getLogger("event_bus")

class EventType(Enum):
    RECORDING_STARTED = 1
    RECORDING_STOPPED = 2
    TRANSCRIPTION_REQUESTED = 3
    TRANSCRIPTION_COMPLETED = 4
    # Add more event types as needed

class ResultQueue:
    """Specialized wrapper for handling transcription results using multiprocessing.Queue."""
    def __init__(self):
        self._queue = Queue()
    def put(self, item):
        self._queue.put(item)
    def get(self):
        return self._queue.get()
    def empty(self):
        return self._queue.empty()

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
        q = self._queues.get(name)
        if isinstance(q, ResultQueue):
            return q._queue
        return q

    def publish(self, event_type: EventType, payload: Any = None):
        with self._event_lock:
            try:
                for callback in self._subscribers[event_type]:
                    callback(payload)
                logger.info(f"Published event: {event_type} with payload: {payload}")
            except Exception as e:
                logger.error(f"Error publishing event {event_type}: {e}")

    def subscribe(self, event_type: EventType, callback: Callable[[Any], None]):
        with self._event_lock:
            try:
                self._subscribers[event_type].append(callback)
                logger.info(f"Subscribed callback to event: {event_type}")
            except Exception as e:
                logger.error(f"Error subscribing to event {event_type}: {e}")

    def unsubscribe(self, event_type: EventType, callback: Callable[[Any], None]):
        with self._event_lock:
            try:
                if callback in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(callback)
                    logger.info(f"Unsubscribed callback from event: {event_type}")
            except Exception as e:
                logger.error(f"Error unsubscribing from event {event_type}: {e}")

    def add_queue(self, name: str):
        with self._event_lock:
            if name not in self._queues:
                self._queues[name] = Queue()

    def add_result_queue(self, name: str):
        with self._event_lock:
            if name not in self._queues:
                self._queues[name] = ResultQueue()

# Implementation will follow in subsequent subtasks. 