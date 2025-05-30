import faster_whisper

model = faster_whisper.WhisperModel("tiny", device="cpu", compute_type="int8")

segments, info = model.transcribe("tests/labeled_audios/sample_001.wav")

for segment in segments:
    print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))

print("Detected language: %s" % info.language)
