import io
import os
import torch
import tempfile
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import soundfile as sf
from TTS.api import TTS as CoquiTTS

from config import NLLB_PATH, WHISPER_PATH, COQUI_MODEL

# ─── Global holders ───────────────────────────────────────────────────────────
nllb_tokenizer    = None
nllb_model        = None
whisper_processor = None   # HuggingFace Whisper processor
whisper_model     = None   # HuggingFace Whisper model
coqui_tts         = None
device            = None


# ─── Startup ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global nllb_tokenizer, nllb_model, whisper_processor, whisper_model, coqui_tts, device

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\nDevice: {'GPU' if torch.cuda.is_available() else 'CPU'}\n")

    # ── 1. NLLB-200-3.3B ──────────────────────────────────────────────────────
    print("Loading NLLB-200-3.3B ...")
    try:
        nllb_tokenizer = AutoTokenizer.from_pretrained(
            NLLB_PATH, local_files_only=True
        )
        nllb_model = AutoModelForSeq2SeqLM.from_pretrained(
            NLLB_PATH, local_files_only=True
        ).to(device)
        print("✅ NLLB-200-3.3B loaded.\n")
    except Exception as e:
        raise RuntimeError(f"NLLB load failed: {e}") from e

    # ── 2. Whisper large-v3-turbo ─────────────────────────────────────────────
    print(f"Loading Whisper from: {WHISPER_PATH}")
    try:
        # Your Whisper is HuggingFace format (model.safetensors)
        # Use WhisperProcessor + WhisperForConditionalGeneration
        whisper_processor = WhisperProcessor.from_pretrained(
            WHISPER_PATH, local_files_only=True
        )
        whisper_model = WhisperForConditionalGeneration.from_pretrained(
            WHISPER_PATH,
            local_files_only=True,
            torch_dtype=torch.float32,
        ).to(device)
        whisper_model.eval()
        print("✅ Whisper loaded.\n")
    except Exception as e:
        print(f"❌ Whisper failed: {e}\n")
        raise RuntimeError(f"Whisper load failed: {e}") from e

    # ── 3. Coqui XTTS v2 ──────────────────────────────────────────────────────
    print("Loading Coqui XTTS v2 ...")
    try:
        coqui_tts = CoquiTTS(COQUI_MODEL)
        coqui_tts.to(str(device))
        print("✅ Coqui XTTS v2 loaded.\n")
    except Exception as e:
        print(f"⚠️  Coqui failed (spoken output disabled): {e}\n")
        coqui_tts = None

    print("🚀 Server ready.\n")
    yield
    print("Shutting down.")


# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="Translator API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


# ─── Schema ───────────────────────────────────────────────────────────────────
class TextRequest(BaseModel):
    text:        str
    source_lang: str   # NLLB code e.g. "ben_Beng"
    target_lang: str   # NLLB code e.g. "eng_Latn"


# ══════════════════════════════════════════════════════════════════════════════
# CORE FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def run_nllb(text: str, src_lang: str, tgt_lang: str) -> str:
    nllb_tokenizer.src_lang = src_lang
    inputs = nllb_tokenizer(
        text, return_tensors="pt",
        padding=True, truncation=True, max_length=512,
    ).to(device)
    target_id = nllb_tokenizer.convert_tokens_to_ids(tgt_lang)
    tokens = nllb_model.generate(
        **inputs,
        forced_bos_token_id=target_id,
        max_length=512, num_beams=4, early_stopping=True,
    )
    return nllb_tokenizer.batch_decode(tokens, skip_special_tokens=True)[0]


# Whisper ISO-639-1 → NLLB code map
WHISPER_TO_NLLB = {
    "af": "afr_Latn", "am": "amh_Ethi", "ar": "arb_Arab", "as": "asm_Beng",
    "az": "azj_Latn", "ba": "bak_Cyrl", "be": "bel_Cyrl", "bn": "ben_Beng",
    "bo": "bod_Tibt", "bs": "bos_Latn", "bg": "bul_Cyrl", "ca": "cat_Latn",
    "cs": "ces_Latn", "cy": "cym_Latn", "da": "dan_Latn", "de": "deu_Latn",
    "el": "ell_Grek", "en": "eng_Latn", "eo": "epo_Latn", "et": "est_Latn",
    "eu": "eus_Latn", "fa": "pes_Arab", "fi": "fin_Latn", "fr": "fra_Latn",
    "gl": "glg_Latn", "gu": "guj_Gujr", "ha": "hau_Latn", "he": "heb_Hebr",
    "hi": "hin_Deva", "hr": "hrv_Latn", "hu": "hun_Latn", "hy": "hye_Armn",
    "id": "ind_Latn", "is": "isl_Latn", "it": "ita_Latn", "ja": "jpn_Jpan",
    "jw": "jav_Latn", "ka": "kat_Geor", "kk": "kaz_Cyrl", "km": "khm_Khmr",
    "kn": "kan_Knda", "ko": "kor_Hang", "lo": "lao_Laoo", "lt": "lit_Latn",
    "lv": "lvs_Latn", "mk": "mkd_Cyrl", "ml": "mal_Mlym", "mn": "khk_Cyrl",
    "mr": "mar_Deva", "ms": "zsm_Latn", "mt": "mlt_Latn", "my": "mya_Mymr",
    "ne": "npi_Deva", "nl": "nld_Latn", "no": "nob_Latn", "pa": "pan_Guru",
    "pl": "pol_Latn", "pt": "por_Latn", "ro": "ron_Latn", "ru": "rus_Cyrl",
    "sd": "snd_Arab", "si": "sin_Sinh", "sk": "slk_Latn", "sl": "slv_Latn",
    "sn": "sna_Latn", "so": "som_Latn", "sq": "als_Latn", "sr": "srp_Cyrl",
    "su": "sun_Latn", "sv": "swe_Latn", "sw": "swh_Latn", "ta": "tam_Taml",
    "te": "tel_Telu", "tg": "tgk_Cyrl", "th": "tha_Thai", "tk": "tuk_Latn",
    "tl": "tgl_Latn", "tr": "tur_Latn", "tt": "tat_Cyrl", "uk": "ukr_Cyrl",
    "ur": "urd_Arab", "uz": "uzn_Latn", "vi": "vie_Latn", "xh": "xho_Latn",
    "yi": "ydd_Hebr", "yo": "yor_Latn", "zh": "zho_Hans", "zu": "zul_Latn",
}

# Coqui XTTS v2 supported language codes
NLLB_TO_COQUI = {
    "eng_Latn": "en", "fra_Latn": "fr", "deu_Latn": "de",
    "spa_Latn": "es", "ita_Latn": "it", "por_Latn": "pt",
    "pol_Latn": "pl", "tur_Latn": "tr", "rus_Cyrl": "ru",
    "nld_Latn": "nl", "ces_Latn": "cs", "arb_Arab": "ar",
    "zho_Hans": "zh-cn", "jpn_Jpan": "ja", "hun_Latn": "hu",
    "kor_Hang": "ko",
}


def run_whisper(audio_bytes: bytes) -> dict:
    """Audio bytes → {text, language (ISO 639-1)}
    Uses HuggingFace WhisperForConditionalGeneration (safetensors format).
    """
    import numpy as np
    import torch

    # Read audio from bytes
    audio_data, sample_rate = sf.read(io.BytesIO(audio_bytes))

    # Stereo → mono
    if audio_data.ndim > 1:
        audio_data = audio_data.mean(axis=1)

    # Resample to 16kHz if needed (Whisper always needs 16kHz)
    if sample_rate != 16000:
        import torchaudio
        waveform  = torch.tensor(audio_data, dtype=torch.float32).unsqueeze(0)
        resampler = torchaudio.transforms.Resample(
            orig_freq=sample_rate, new_freq=16000
        )
        audio_data = resampler(waveform).squeeze(0).numpy()

    # Process with WhisperProcessor — produces input_features tensor
    inputs = whisper_processor(
        audio_data,
        sampling_rate=16000,
        return_tensors="pt",
    )

    # Force float32 on every tensor so CPU does not crash with float16 weights
    inputs = {k: v.to(torch.float32).to(device) for k, v in inputs.items()}

    # Generate transcription
    with torch.no_grad():
        predicted_ids = whisper_model.generate(
            inputs["input_features"],
            task="transcribe",
        )

    # Decode tokens → text
    transcription = whisper_processor.batch_decode(
        predicted_ids, skip_special_tokens=True
    )[0].strip()

    # Detect language from the first decoder token
    with torch.no_grad():
        logits = whisper_model(
            inputs["input_features"],
            decoder_input_ids=torch.tensor(
                [[whisper_model.config.decoder_start_token_id]]
            ).to(device),
        ).logits

    lang_token_id = logits[0, 0].argmax().item()
    lang_token    = whisper_processor.tokenizer.convert_ids_to_tokens(
        [lang_token_id]
    )[0]
    # token looks like "<|en|>" → extract "en"
    detected_lang = lang_token.strip("<|>") if "<|" in lang_token else "en"

    return {
        "text":     transcription,
        "language": detected_lang,
    }


def run_coqui(text: str, nllb_tgt: str) -> str:
    """Translated text + NLLB target code → path to spoken WAV file"""
    coqui_lang = NLLB_TO_COQUI.get(nllb_tgt, "en")
    out_path   = tempfile.mktemp(suffix=".wav")
    coqui_tts.tts_to_file(text=text, language=coqui_lang, file_path=out_path)
    return out_path


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    return {"status": "ok"}


@app.get("/health")
async def health():
    if nllb_model is None:
        raise HTTPException(status_code=503, detail="Models not loaded.")
    return {
        "status":  "healthy",
        "device":  str(device),
        "nllb":    nllb_model    is not None,
        "whisper": whisper_model is not None,
        "tts":     coqui_tts     is not None,
    }


# ── 1. Plain text translation ─────────────────────────────────────────────────
@app.post("/translate")
async def translate_text(req: TextRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Input text is empty.")
    try:
        result = run_nllb(req.text, req.source_lang, req.target_lang)
        return {
            "original_text":   req.text,
            "translated_text": result,
            "source_lang":     req.source_lang,
            "target_lang":     req.target_lang,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation error: {e}")


# ── 2. Full voice pipeline ────────────────────────────────────────────────────
#   Microphone audio
#        ↓  Whisper large-v3-turbo  (transcribe + detect language)
#        ↓  NLLB-200-3.3B           (translate to target language)
#        ↓  Coqui XTTS v2           (speak the translation)
#        ↓  WAV file returned to browser
@app.post("/voice-translate")
async def voice_translate(
    audio:       UploadFile = File(...),
    target_lang: str        = Form(default="eng_Latn"),
):
    if whisper_model is None:
        raise HTTPException(status_code=503, detail="Whisper not loaded.")
    if nllb_model is None:
        raise HTTPException(status_code=503, detail="NLLB not loaded.")

    try:
        audio_bytes = await audio.read()

        # Step 1 — Whisper: audio → text + detected language
        w = run_whisper(audio_bytes)
        transcribed   = w["text"]
        detected_iso  = w["language"]                          # e.g. "bn"
        nllb_src      = WHISPER_TO_NLLB.get(detected_iso, "eng_Latn")

        # Step 2 — NLLB: text → translated text
        translated = run_nllb(transcribed, nllb_src, target_lang)

        # Step 3 — Coqui (if available): translated text → spoken WAV
        if coqui_tts is not None:
            wav_path = run_coqui(translated, target_lang)
            return FileResponse(
                wav_path,
                media_type="audio/wav",
                filename="translation.wav",
                headers={
                    "X-Transcribed":   transcribed,
                    "X-Translated":    translated,
                    "X-Detected-Lang": detected_iso,
                },
            )
        else:
            # TTS not available — return text only
            return {
                "transcribed":   transcribed,
                "translated":    translated,
                "detected_lang": detected_iso,
                "tts":           False,
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice pipeline error: {e}")