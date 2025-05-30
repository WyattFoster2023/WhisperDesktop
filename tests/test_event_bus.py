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

def test_integration_with_mock_subscribers():
    bus = EventBus()
    called = []
    def mock_subscriber_1(payload):
        called.append(('s1', payload))
    def mock_subscriber_2(payload):
        called.append(('s2', payload))
    bus.subscribe(EventType.TRANSCRIPTION_COMPLETED, mock_subscriber_1)
    bus.subscribe(EventType.TRANSCRIPTION_COMPLETED, mock_subscriber_2)
    bus.publish(EventType.TRANSCRIPTION_COMPLETED, {'result': 'ok'})
    assert ('s1', {'result': 'ok'}) in called
    assert ('s2', {'result': 'ok'}) in called
    bus.unsubscribe(EventType.TRANSCRIPTION_COMPLETED, mock_subscriber_1)
    bus.unsubscribe(EventType.TRANSCRIPTION_COMPLETED, mock_subscriber_2) 