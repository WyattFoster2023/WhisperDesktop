
# Product Requirements Document (PRD): Windows Local Transcription Tool

> **Edit Notice:**  
> This PRD captures the current, approved scope and architecture.  
> **Any change** to features, workflows, or system design **must** result in an update to this document.

---

## 1. Purpose & Scope

- **Objective:** Provide a reliable, segment‑based audio transcription desktop app for Windows, using Faster‑Whisper.  
- **Key Goals:**  
  1. **Crash‑proof** audio capture  
  2. **Immediate** segment transcription  
  3. **Simple**, always‑on‑top UI overlay  
  4. **Automatic** persistence, cleanup, and clipboard integration  

This is a SOLID project. All code it to be written in such a way that is:

- S – Single Responsibility Principle: A class/module should only have one reason to change.

- O – Open/Closed Principle: Software entities should be open for extension but closed for modification.

- L – Liskov Substitution Principle: Objects of a superclass should be replaceable with objects of a subclass.

- I – Interface Segregation Principle: Prefer many specific interfaces over one general-purpose interface.

- D – Dependency Inversion Principle: Depend on abstractions, not concretions.

This is also a github project, use commits to save task-master task progress.

---

## 2. Functional Requirements

### 2.1 Recording Modes  
- **Push‑to‑Talk:** Hold button to record; release stops.  
- **Toggle Recording:** Click to start; click again to stop.  
- **Shared Logic:** Both modes invoke the same recording → save → enqueue → transcribe pipeline.

### 2.2 Transcription & Segmentation  
- **Backend:** Faster‑Whisper `WhisperModel.transcribe(…)` with model and device options made accessible. 
- **Segments:** Automatic start/end timestamps; no hard time limits per segment.  
- **VAD Filtering:** Remove >2s (configurable) silence by default.  
- **Batching:** Optionally use `BatchedInferencePipeline` for high‑volume jobs.

### 2.3 Storage & Data Management  
- **Audio Files:**  
  - Saved immediately to disk (`recording_YYYY‑MM‑DD_hh‑mm‑ss.wav`)  
  - Retained until successful transcription & database save  
  - Deleted automatically upon confirmation  
- **Transcriptions:**  
  - Persisted to a local database (e.g., SQLite or PostgreSQL)  
  - Schema: `{ id, timestamp, text, segments_metadata, audio_path (nullable) }`

### 2.4 User Interface  
- **Overlay:** Small always‑on‑top window with:  
  - Record/Stop buttons  
  - Status indicator: “Recording…”, “Transcribing…”, “Saved ✓”  
  - Spinner or progress bar during transcription  
- **History Dropdown:**  
  - Shows recent items: timestamp + first 15 words  
  - Selecting an item reveals full text + “Copy” button  
- **Clipboard Integration:**  
  - Auto‑copy each new transcript  
  - Optional “Paste” via simulated Ctrl+V in active window 

### 2.5 External resources

`https://github.com/SYSTRAN/faster-whisper/blob/master/README.md` can provide the actual README for faster-whisper. Use a internet tool to find out more.

---

## 3. Non‑Functional Requirements

- **Responsiveness:** UI must remain interactive during transcription.  
- **Reliability:** Audio files must survive app or system crashes.  
- **Performance:**  
  - CPU: INT8 mode on multi‑core  
  - GPU (optional): FP16/INT8 with batch_size=8 for fastest throughput  
- **Extensibility:** Follow SOLID principles; decoupled modules for easy future changes.

---

## 4. System Architecture & Workflow

```text
[ UI Overlay ]                                  
      │   user action (record/stop)              
      ▼                                          
[ Recorder Module ] —–save file—–▶ [ recordings/…wav ]
      │ enqueue job                                  
      ▼                                            
[ multiprocessing.Queue ] ──▶ [ Transcriber Worker ]
                                           │ process via Faster‑Whisper
                                           ▼
                               [ Result Queue / Event ]
                                           │
                                           ▼
[ Main/UI Thread ] — save_to_db → delete audio → copy_to_clipboard → update UI
````

### 4.1 Modules

1. **Recorder**

   * Handles mic input, file flush, crash safety
2. **Transcriber Worker**

   * Background process: `model.transcribe(…)`, builds full text
3. **Storage Manager**

   * Database CRUD; audio–file lifecycle
4. **UI Controller**

   * Overlay, status, history dropdown
5. **Clipboard Controller**

   * Clipboard write; optional Ctrl+V simulation
6. **Event Bus**

   * Queue-based decoupling between modules

---

## 5. Success Criteria

* **Functionality:**

  * ≥ 95% uptime during recording/transcription
  * No data loss on forced app termination
* **Usability:**

  * Transcription results visible within 1–2 s of job completion
  * History browsing & copy/paste intuitive
* **Performance:**

  * Real‑time (segment) throughput ≥ 1× audio length on modern hardware

---

## 6. Change Control

> **IMPORTANT:** This PRD is a living document.
> **All** feature additions, removals, or architectural changes **must** be reflected here **before** implementation.

# Change Log

> Version: 1.0<br>
> Author: Wyatt<br>
> Summary: <br>
> * Added initial PRD
> * Encouraged improvments, but changes must be maintained here.