import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from src.event_bus.event_bus import EventBus, EventType

def test_singleton():
    bus1 = EventBus()
    bus2 = EventBus()
    assert bus1 is bus2

def test_publish_subscribe():
    bus = EventBus()
    results = []
    def callback(payload):
        results.append(payload)
    bus.subscribe(EventType.RECORDING_STARTED, callback)
    bus.publish(EventType.RECORDING_STARTED, {'foo': 'bar'})
    assert results == [{'foo': 'bar'}]
    bus.unsubscribe(EventType.RECORDING_STARTED, callback)
    results.clear()
    bus.publish(EventType.RECORDING_STARTED, {'foo': 'baz'})
    assert results == []

def test_queue_operations():
    bus = EventBus()
    q = bus.get_queue('transcription')
    q.put('test')
    assert q.get() == 'test'

def test_error_handling():
    bus = EventBus()
    # Subscribe a callback that raises
    def bad_callback(payload):
        raise ValueError('fail')
    bus.subscribe(EventType.RECORDING_STOPPED, bad_callback)
    # Should not raise, error is logged
    bus.publish(EventType.RECORDING_STOPPED, None)
    bus.unsubscribe(EventType.RECORDING_STOPPED, bad_callback) 