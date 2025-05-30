import json
from datetime import datetime
from pathlib import Path
from src.transcriber.transcriber_worker import TranscriberWorker
from src.event_bus.event_bus import EventBus
import multiprocessing
import time
import re

def soft_equal(a, b):
    # Case-insensitive, ignore whitespace and punctuation
    def norm(s):
        return re.sub(r'\W+', '', s).strip().lower()
    return norm(a) == norm(b)

def main():
    folder = Path('tests/labeled_audios')
    files_json = folder / 'files.json'
    with open(files_json, 'r', encoding='utf-8') as f:
        entries = json.load(f)
    event_bus = EventBus()
    transcription_queue = event_bus.get_queue('transcription')
    result_queue = event_bus.get_queue('result')
    matches = 0
    total = 0
    for entry in entries:
        audio_path = Path(entry['file'])
        if not audio_path.is_absolute():
            audio_path = folder / audio_path
        audio_path = audio_path.relative_to(Path.cwd()) if audio_path.is_absolute() else audio_path
        transcription_queue.queue.clear()
        result_queue.queue.clear()
        transcription_queue.put(str(audio_path))
        worker = TranscriberWorker(max_loops=1)
        worker.start()
        worker.join(timeout=60)
        last_transcription = None
        if not result_queue.empty():
            result = result_queue.get()
            last_transcription = result['text']
        entry['last_transcription'] = last_transcription
        entry['datestamp'] = datetime.now().isoformat()
        if last_transcription is not None and 'ground_truth' in entry:
            entry['match'] = soft_equal(last_transcription, entry['ground_truth'])
            if entry['match']:
                matches += 1
            total += 1
        else:
            entry['match'] = None
    with open(files_json, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    print(f"Soft matches: {matches}/{total}")

if __name__ == '__main__':
    main() 