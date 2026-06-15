# Offline Multilingual Translator — Project Explanation

---

## 1. What This Project Does

This is a **fully offline AI-powered translator** that works like Google Translate
but runs entirely on your local machine. No internet needed after setup.
No data ever leaves your computer.

It supports:
- **Text translation** — type text, get translation (200 languages)
- **Voice translation** — speak into mic, get translated text + spoken audio back

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────┐
│              USER (Browser)                      │
│         Streamlit Frontend (app.py)              │
└─────────────────┬───────────────────────────────┘
                  │  HTTP requests (localhost:8000)
┌─────────────────▼───────────────────────────────┐
│         FastAPI Backend (NLLB.py)                │
│                                                  │
│  ┌─────────────┐  ┌──────────┐  ┌────────────┐  │
│  │ NLLB-200    │  │ Whisper  │  │ Coqui TTS  │  │
│  │ 3.3B params │  │ large-   │  │ XTTS v2    │  │
│  │ 200 langs   │  │ v3-turbo │  │ 16 langs   │  │
│  │ Text→Text   │  │ Audio→   │  │ Text→Audio │  │
│  │             │  │ Text     │  │            │  │
│  └─────────────┘  └──────────┘  └────────────┘  │
└─────────────────────────────────────────────────┘
                  │  All models load from local disk
┌─────────────────▼───────────────────────────────┐
│              config.py                           │
│   NLLB_PATH, WHISPER_PATH, COQUI_MODEL          │
└─────────────────────────────────────────────────┘
```

---

## 3. Project File Structure

```
translator_app/
│
├── NLLB.py          ← FastAPI backend — all AI models + API routes
├── app.py           ← Streamlit frontend — UI + user interaction
├── config.py        ← All model paths in one place (edit once per machine)
└── PROJECT_EXPLANATION.md  ← this file
```

**Why 3 separate files?**
- `config.py` means anyone can run this project by only editing their paths once
- `NLLB.py` is pure backend — no UI code
- `app.py` is pure frontend — no model code


---

## 4. config.py — Configuration

```python
NLLB_PATH    = r"C:\Users\...\nllb-200-3.3B"
WHISPER_PATH = r"C:\Users\...\whisper-large-v3-turbo"
COQUI_MODEL  = "tts_models/multilingual/multi-dataset/xtts_v2"
CHAR_LIMIT   = 5000
CHAR_WARN_AT = 4500
```

**Why this exists:**
When sharing code with others, they only change this one file.
The main code files never need to be touched for setup.

---

## 5. NLLB.py — Backend (FastAPI)

### How models load at startup

FastAPI uses a `lifespan` function — this runs ONCE when the server starts,
loads all 3 models into RAM, and keeps them there forever.
This is why startup is slow (2–5 min) but requests after that are faster.

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load NLLB → Whisper → Coqui into memory once
    # Server then handles requests until shutdown
```

**Why load everything at startup instead of per-request?**
Loading a 3.3B parameter model takes 30–60 seconds. If we loaded on each
request the user would wait a minute every single time. Loading once means
the model stays in RAM ready to go.

---

### API Routes — All 4 Endpoints

#### Route 1: GET /health
```
URL:     GET http://localhost:8000/health
Purpose: Check if server + all models are loaded and ready
Returns: { status, device, nllb, whisper, tts }
Used by: Streamlit frontend to show the green "API ONLINE" badge
```

Example response:
```json
{
  "status":  "healthy",
  "device":  "cpu",
  "nllb":    true,
  "whisper": true,
  "tts":     true
}
```

---

#### Route 2: POST /translate
```
URL:     POST http://localhost:8000/translate
Purpose: Translate typed text using NLLB-200-3.3B
Input:   { text, source_lang, target_lang }
Returns: { original_text, translated_text }
Used by: The "TRANSLATE →" button in the UI
```

Example request:
```json
{
  "text":        "Good morning",
  "source_lang": "eng_Latn",
  "target_lang": "ben_Beng"
}
```

Example response:
```json
{
  "original_text":   "Good morning",
  "translated_text": "শুভ সকাল"
}
```

**How NLLB translation works inside:**
```
1. Set tokenizer source language
2. Convert text → tokens (numbers the model understands)
3. Run model.generate() with target language forced as first token
4. Decode output tokens → human-readable text
```

Language codes use NLLB format: `eng_Latn`, `ben_Beng`, `fra_Latn` etc.
Format is always: `{language}_{script}`

---

#### Route 3: POST /voice-submit  ← The most important route
```
URL:     POST http://localhost:8000/voice-submit
Purpose: Start the 3-model voice pipeline in a BACKGROUND THREAD
Input:   audio file (WAV/MP3) + target_lang
Returns: { job_id } — immediately, within 1 second
Used by: UI mic button after user records voice
```

**Why background thread?**

This is the key engineering decision. The voice pipeline takes 2–15 minutes on CPU:
```
Whisper transcription:  8–15 sec
NLLB translation:       3–8  sec
Coqui TTS:              5–12 sec
Total:                  ~25  sec minimum on CPU
```

If we ran this synchronously (blocking), the HTTP connection would time out
before it finishes and the user would get an error. By putting it in a
background thread, the API returns a `job_id` in 1 second, and the pipeline
runs separately. The UI then polls for the result.

**The Job Queue pattern:**
```python
JOBS = {}  # Dictionary: { job_id: { status, result } }

# Route 3 — called once, returns immediately
def voice_submit(audio, target_lang):
    job_id = uuid.uuid4()           # unique ID like "a3f8-..."
    JOBS[job_id] = {"status": "pending"}
    threading.Thread(target=run_pipeline, args=(job_id, audio)).start()
    return {"job_id": job_id}       # returned to UI in < 1 second
```

---

#### Route 4: GET /voice-status/{job_id}
```
URL:     GET http://localhost:8000/voice-status/a3f8-...
Purpose: Check if background pipeline is finished
Returns: { status: "pending|done|error", step, transcribed, translated, wav_b64 }
Used by: UI polls this every 3 seconds until status == "done"
```

The UI keeps calling this route repeatedly until it gets `"status": "done"`.

**Step values during processing:**
```
"queued"   → just submitted, not started yet
"whisper"  → Whisper is transcribing your voice
"nllb"     → NLLB is translating the text
"tts"      → Coqui is generating speech audio
"done"     → everything finished, result ready
"error"    → something failed
```

When done, the response includes:
```json
{
  "status":      "done",
  "transcribed": "Good morning",
  "translated":  "শুভ সকাল",
  "detected":    "en",
  "wav_b64":     "UklGRi4A..."  ← audio file as base64 string
}
```

The audio is returned as **base64** (text encoding of binary) because
JSON cannot contain raw binary data.

---

### The Full Voice Pipeline Flow (inside _run_pipeline function)

```
Step 1 — WHISPER (Speech to Text)
  Audio bytes
    → Read with soundfile library
    → Resample to 16kHz (Whisper always needs 16kHz)
    → WhisperProcessor converts to mel spectrogram features
    → WhisperForConditionalGeneration.generate() → token IDs
    → Decode token IDs → transcribed text
    → Detect language from first decoder output token

Step 2 — NLLB (Text to Text Translation)
  Transcribed text + detected language
    → Map Whisper's 2-letter code (e.g. "en") to NLLB code (e.g. "eng_Latn")
    → Tokenize with NLLB tokenizer
    → nllb_model.generate() with forced target language token
    → Decode → translated text

Step 3 — COQUI XTTS v2 (Text to Speech)
  Translated text + target language
    → Map NLLB code (e.g. "ben_Beng") to Coqui code (e.g. "bn")
    → coqui_tts.tts_to_file() → WAV file on disk
    → Read WAV file → encode as base64 → return in JSON
```

---

## 6. app.py — Frontend (Streamlit)

### How Streamlit works (important to understand)

Streamlit **reruns the entire Python file from top to bottom** on every
user interaction. This is different from regular web apps. Session state
(`st.session_state`) is used to remember things between reruns.

---

### Key UI Sections

#### Header + Health Badge
```python
check_health()  # calls GET /health every 30 seconds
                # shows green badge if online, red if offline
```

#### Language Dropdowns — Why native HTML instead of Streamlit widgets?

The language dropdowns are built with native HTML `<select>` tags, NOT
Streamlit's `st.selectbox`. Reason: Streamlit's selectbox adds extra
padding, borders, and styling that couldn't be customized to match the
dark theme. Native HTML gives full CSS control.

The trick: hidden Streamlit selectboxes exist but are invisible (display:none).
The HTML dropdowns update these hidden widgets via JavaScript, which triggers
a Streamlit rerun to update the session state.

```
User picks language in HTML dropdown
  → JavaScript reads the value
  → JavaScript clicks a hidden Streamlit button
  → Streamlit reruns
  → Session state updates with new language
```

#### Swap Button (⇄)
Swaps `src_lang` and `tgt_lang` in session state, triggers rerun.
Simple but needs careful handling to not reset the translation output.

#### Input Card — Textarea + Mic Button

The mic button (`audio_recorder`) sits INSIDE the input card.
Custom CSS makes it look like it belongs there naturally.

```
┌─────────────────────────────────┐
│ Type or paste text here...      │
│                                 │
│                                 │
├─────────────────────────────────┤
│ 🎤 Click mic · click again stop │  ← mic bar
└─────────────────────────────────┘
```

#### The MD5 Hash Problem and Solution

`audio_recorder` has a quirk: it returns the recorded audio bytes
on EVERY Streamlit rerun, not just once. Without protection, this causes:

```
User records → bytes returned → sent to API → rerun triggered
→ bytes returned AGAIN → sent to API AGAIN → infinite loop
```

Fix: store an MD5 hash of the last sent audio in session state.
Compare on every render. Only send to API if hash is different (new recording).

```python
audio_hash = hashlib.md5(audio_bytes).hexdigest()
if audio_hash != st.session_state.last_audio_hash:
    # This is a new recording — safe to send
```

#### Text Translation Flow
```
User types text → clicks TRANSLATE →
  → POST /translate with text + lang codes
  → response stored in session_state.translation
  → page reruns → output box shows result
```

#### Voice Translation Flow
```
User clicks mic → records → clicks mic again to stop
  → audio_bytes captured
  → Preview audio shown so user confirms recording
  → User clicks "▶ TRANSLATE VOICE →"
  → POST /voice-submit → get job_id back immediately
  → Poll GET /voice-status/{job_id} every 3 seconds
  → Show step progress: Whisper → NLLB → Coqui
  → When done: show transcription + translation + play audio
```

---

## 7. The 3 AI Models — Explained Simply

### NLLB-200-3.3B (Meta AI)
- **What:** No Language Left Behind — Meta's multilingual translation model
- **Size:** 3.3 billion parameters, ~13GB on disk
- **Languages:** 200 languages
- **How it works:** Encoder-Decoder transformer. Encodes source text,
  decodes to target language. Uses "forced BOS token" to force output language.
- **Format:** HuggingFace safetensors
- **Speed on CPU:** 3–8 seconds per sentence

### Whisper large-v3-turbo (OpenAI)
- **What:** Speech recognition model that transcribes audio to text
- **Size:** ~1.5GB
- **Languages:** 100+ languages, auto-detects which one
- **How it works:** Converts audio to mel spectrogram (visual representation
  of sound frequencies), then transformer processes it like an image
- **Format:** HuggingFace safetensors (model.safetensors)
- **Note:** Needs 16kHz mono audio — we resample automatically
- **Speed on CPU:** 8–15 seconds per 5-second clip

### Coqui XTTS v2
- **What:** Text-to-Speech — converts text to spoken audio
- **Size:** ~1.8GB
- **Languages:** 16 languages for voice output
- **How it works:** Takes text + language code → generates WAV audio file
- **Format:** Loads from AppData cache automatically
- **Speed on CPU:** 5–12 seconds

---

## 8. Language Code Systems — 3 Different Formats

This was one of the trickiest parts of the project. Each model uses different codes:

| Language | NLLB code | Whisper code | Coqui code |
|----------|-----------|--------------|------------|
| English  | eng_Latn  | en           | en         |
| Bengali  | ben_Beng  | bn           | (not supported) |
| French   | fra_Latn  | fr           | fr         |
| Hindi    | hin_Deva  | hi           | (not supported) |
| Japanese | jpn_Jpan  | ja           | ja         |

We maintain two mapping dictionaries:
- `WHISPER_TO_NLLB` — converts Whisper's 2-letter code to NLLB code
- `NLLB_TO_COQUI`   — converts NLLB code to Coqui code for TTS

---

## 9. What Could Be Improved

### Performance (Biggest Wins)
| Improvement | Impact | Effort |
|-------------|--------|--------|
| Get an NVIDIA GPU (RTX 3060+) | 10–20x faster, near real-time | Buy hardware |
| Switch to NLLB-600M distilled | 5x faster NLLB, slightly lower quality | 30 min |
| Switch to Whisper-small | 10x faster Whisper, slightly lower accuracy | 30 min |
| Run Whisper + NLLB in parallel | 30% faster pipeline | Medium code change |

### Features
| Feature | Description |
|---------|-------------|
| Streaming output | Show translation word by word as model generates |
| Translation history | Save past translations in a database |
| Confidence score | Show how confident the model is |
| Copy button | One-click copy translated text |
| Auto-detect language | Let NLLB auto-detect source language like Google |

### Code Quality
| Improvement | Description |
|-------------|-------------|
| Docker container | Package everything so anyone can run with one command |
| .env file | Move config.py to environment variables (more professional) |
| Unit tests | Test each model function independently |
| Logging | Proper log files instead of print statements |
| Error retry | Auto-retry failed translations once before showing error |

### Architecture
| Improvement | Description |
|-------------|-------------|
| WebSocket | Real-time progress updates without polling |
| Redis queue | Professional job queue instead of in-memory dict (JOBS{}) |
| Multiple workers | Run 2 uvicorn workers for concurrent requests |

---

## 10. How to Run

```bash
# Terminal 1 — Start AI backend
uvicorn NLLB:app --reload

# Terminal 2 — Start UI
streamlit run app.py

# Open browser
http://localhost:8501
```

**Startup sequence (watch Terminal 1):**
```
Loading NLLB-200-3.3B ...     ← takes ~60 seconds
✅ NLLB loaded.
Loading Whisper ...            ← takes ~30 seconds
✅ Whisper loaded.
Loading Coqui XTTS v2 ...     ← takes ~20 seconds
✅ Coqui loaded.
🚀 Server ready.              ← NOW open the browser
```

---

## 11. Key Technical Decisions and Why

| Decision | Why |
|----------|-----|
| FastAPI for backend | Async, fast, automatic Swagger docs at /docs |
| Streamlit for frontend | Rapid development, Python only, no HTML/JS needed |
| Background thread for voice | Prevents HTTP timeout on slow CPU inference |
| MD5 hash check | Stops Streamlit's rerun loop from re-sending audio |
| Native HTML select | Full CSS control for dark theme dropdowns |
| local_files_only=True | Guarantees models never download from internet |
| torch.float32 forced | Prevents float16/float32 dtype mismatch crash on CPU |
| config.py separation | Makes project portable — one file to edit per machine |

---

*Built with: Python · FastAPI · Streamlit · HuggingFace Transformers · PyTorch · Coqui TTS*
*Models: Meta NLLB-200-3.3B · OpenAI Whisper large-v3-turbo · Coqui XTTS v2*
