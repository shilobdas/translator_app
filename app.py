import streamlit as st
import requests
from audio_recorder_streamlit import audio_recorder
from config import CHAR_LIMIT, CHAR_WARN_AT

# ══════════════════════════════════════════════════════════════════════════════
API_BASE         = "http://localhost:8000"
DEFAULT_SRC_LANG = "Bengali"
DEFAULT_TGT_LANG = "English"
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(page_title="Translator", page_icon="🌐", layout="centered")

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
.stApp { background-color: #0d0f14; color: #e8eaf0; }

/* ── Header ── */
.header-block {
    border-left: 4px solid #00e5ff;
    padding: 0.4rem 1rem 0.4rem 1.2rem;
    margin-bottom: 1.8rem;
}
.header-block h1 {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 2rem; font-weight: 600;
    color: #00e5ff; margin: 0; letter-spacing: -0.5px;
}
.header-block p {
    font-size: 0.82rem; color: #7a8099;
    margin: 0.2rem 0 0 0; font-family: 'IBM Plex Mono', monospace;
}

/* ── Badges ── */
.badge {
    display: inline-block;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem; padding: 3px 10px;
    border-radius: 20px; margin-bottom: 1.4rem;
}
.badge-ok  { background:#003d2e; color:#00e5a0; border:1px solid #00e5a033; }
.badge-err { background:#3d0010; color:#ff5a7a; border:1px solid #ff5a7a33; }

/* ── Field label ── */
.field-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem; color: #00e5ff;
    letter-spacing: 1.5px; text-transform: uppercase;
    margin-bottom: 0.4rem;
}

/* ── Language row ── */
.lang-row {
    display: grid;
    grid-template-columns: 1fr 44px 1fr;
    align-items: end;
    gap: 8px;
    margin-bottom: 0.8rem;
}
.swap-circle {
    width: 44px; height: 44px;
    background: #141720; border: 1px solid #1e2333;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; color: #00e5ff;
    cursor: pointer;
    transition: background 0.2s, transform 0.35s;
    margin-bottom: 2px;
}
.swap-circle:hover { background: #1e2333; transform: rotate(180deg); }

/* ── Native select ── */
.native-select {
    width: 100%; height: 46px;
    padding: 0 36px 0 12px;
    background: #141720; color: #e8eaf0;
    border: 1px solid #1e2333; border-radius: 8px;
    font-family: 'IBM Plex Sans', sans-serif; font-size: 0.9rem;
    cursor: pointer; appearance: none; -webkit-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%2300e5ff' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
    background-repeat: no-repeat; background-position: right 12px center;
    outline: none; transition: border-color 0.2s;
}
.native-select:focus { border-color: #00e5ff; }
.native-select option { background: #141720; color: #e8eaf0; }

/* ── Input card — wraps textarea + mic button ── */
.input-card {
    background: #141720;
    border: 1px solid #1e2333;
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 0.8rem;
}
.input-card:focus-within { border-color: #00e5ff44; }

/* ── Textarea inside card ── */
div[data-testid="stTextArea"] label { display: none !important; }
div[data-testid="stTextArea"] > div {
    border: none !important; box-shadow: none !important; padding: 0 !important;
}
div[data-testid="stTextArea"] textarea {
    background: #141720 !important; color: #e8eaf0 !important;
    border: none !important; border-radius: 0 !important;
    box-shadow: none !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 1rem !important; line-height: 1.7 !important;
    padding: 14px !important; resize: none !important;
    caret-color: #00e5ff !important;
}
div[data-testid="stTextArea"] textarea:focus {
    box-shadow: none !important; outline: none !important;
}
div[data-testid="stTextArea"] textarea::placeholder { color: #3a4060 !important; }

/* ── Mic bar inside input card ── */
.mic-bar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 14px;
    border-top: 1px solid #1e2333;
    background: #0f111a;
}
.mic-hint {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem; color: #3a4060;
}

/* Make audio_recorder button match our theme */
div[data-testid="stAudioRecorder"] button {
    background: #141720 !important;
    border: 1px solid #1e2333 !important;
    border-radius: 50% !important;
    color: #00e5ff !important;
    transition: background 0.2s !important;
}
div[data-testid="stAudioRecorder"] button:hover {
    background: #1e2333 !important;
}

/* ── Output box ── */
.output-box {
    background: #0a0c10;
    border: 1px solid #00e5ff33;
    border-radius: 8px; padding: 1.2rem 1.4rem;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 1.05rem; color: #e8eaf0;
    min-height: 90px; line-height: 1.7;
    word-break: break-word; margin-bottom: 0.4rem;
}
.output-tag {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem; color: #3a4060; margin-bottom: 0.3rem;
}

/* ── Whisper result box ── */
.whisper-box {
    background: #0f111a;
    border: 1px solid #1e2333;
    border-radius: 8px; padding: 0.8rem 1rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.82rem; color: #7a8099;
    margin-bottom: 0.8rem;
}
.whisper-box span { color: #00e5ff; }

/* ── Translate button ── */
div.stButton > button {
    width: 100%; background: #00e5ff; color: #0d0f14;
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 600; font-size: 0.9rem; letter-spacing: 1px;
    border: none; border-radius: 8px; padding: 0.65rem 0;
    cursor: pointer; transition: background 0.2s;
}
div.stButton > button:hover { background: #33ecff; }
div.stButton > button[kind="secondary"] {
    background: #141720 !important; color: #7a8099 !important;
    border: 1px solid #1e2333 !important;
    font-size: 0.82rem !important; letter-spacing: 0.5px !important;
}
div.stButton > button[kind="secondary"]:hover {
    background: #1e2333 !important; color: #00e5ff !important;
}

/* char count */
.char-count { font-family:'IBM Plex Mono',monospace; font-size:0.72rem; color:#3a4060; }
.char-warn  { color:#ff5a7a !important; }

/* hide Streamlit native selectboxes — we use HTML native ones */
div[data-testid="stSelectbox"] { display: none !important; }
label { color: #7a8099 !important; font-size: 0.82rem !important; }
hr { border-color: #1e2333; }
</style>
""", unsafe_allow_html=True)

# ─── All 200 NLLB Languages ────────────────────────────────────────────────────
LANGUAGES = {
    "Acehnese (Arabic script)":"ace_Arab","Acehnese (Latin script)":"ace_Latn",
    "Mesopotamian Arabic":"acm_Arab","Ta'izzi-Adeni Arabic":"acq_Arab",
    "Tunisian Arabic":"aeb_Arab","Afrikaans":"afr_Latn",
    "South Levantine Arabic":"ajp_Arab","Akan":"aka_Latn","Amharic":"amh_Ethi",
    "North Levantine Arabic":"apc_Arab","Modern Standard Arabic":"arb_Arab",
    "Najdi Arabic":"ars_Arab","Moroccan Arabic":"ary_Arab",
    "Egyptian Arabic":"arz_Arab","Assamese":"asm_Beng","Asturian":"ast_Latn",
    "Awadhi":"awa_Deva","Central Aymara":"ayr_Latn",
    "South Azerbaijani":"azb_Arab","North Azerbaijani":"azj_Latn",
    "Bashkir":"bak_Cyrl","Bambara":"bam_Latn","Balinese":"ban_Latn",
    "Belarusian":"bel_Cyrl","Bemba":"bem_Latn","Bengali":"ben_Beng",
    "Bhojpuri":"bho_Deva","Banjar (Arabic script)":"bjn_Arab",
    "Banjar (Latin script)":"bjn_Latn","Standard Tibetan":"bod_Tibt",
    "Bosnian":"bos_Latn","Buginese":"bug_Latn","Bulgarian":"bul_Cyrl",
    "Catalan":"cat_Latn","Cebuano":"ceb_Latn","Czech":"ces_Latn",
    "Chokwe":"cjk_Latn","Central Kurdish":"ckb_Arab","Crimean Tatar":"crh_Latn",
    "Welsh":"cym_Latn","Danish":"dan_Latn","German":"deu_Latn",
    "Southwestern Dinka":"dik_Latn","Dyula":"dyu_Latn","Dzongkha":"dzo_Tibt",
    "Greek":"ell_Grek","English":"eng_Latn","Esperanto":"epo_Latn",
    "Estonian":"est_Latn","Basque":"eus_Latn","Ewe":"ewe_Latn",
    "Faroese":"fao_Latn","Fijian":"fij_Latn","Finnish":"fin_Latn",
    "Fon":"fon_Latn","French":"fra_Latn","Friulian":"fur_Latn",
    "Nigerian Fulfulde":"fuv_Latn","Scottish Gaelic":"gla_Latn",
    "Irish":"gle_Latn","Galician":"glg_Latn","Guarani":"grn_Latn",
    "Gujarati":"guj_Gujr","Haitian Creole":"hat_Latn","Hausa":"hau_Latn",
    "Hebrew":"heb_Hebr","Hindi":"hin_Deva","Chhattisgarhi":"hne_Deva",
    "Croatian":"hrv_Latn","Hungarian":"hun_Latn","Armenian":"hye_Armn",
    "Igbo":"ibo_Latn","Ilocano":"ilo_Latn","Indonesian":"ind_Latn",
    "Icelandic":"isl_Latn","Italian":"ita_Latn","Javanese":"jav_Latn",
    "Japanese":"jpn_Jpan","Kabyle":"kab_Latn","Jingpho":"kac_Latn",
    "Kamba":"kam_Latn","Kannada":"kan_Knda",
    "Kashmiri (Arabic script)":"kas_Arab",
    "Kashmiri (Devanagari script)":"kas_Deva","Georgian":"kat_Geor",
    "Central Kanuri (Arabic script)":"knc_Arab",
    "Central Kanuri (Latin script)":"knc_Latn","Kazakh":"kaz_Cyrl",
    "Kabiyè":"kbp_Latn","Kabuverdianu":"kea_Latn","Khmer":"khm_Khmr",
    "Kikuyu":"kik_Latn","Kinyarwanda":"kin_Latn","Kyrgyz":"kir_Cyrl",
    "Kimbundu":"kmb_Latn","Northern Kurdish":"kmr_Latn","Kikongo":"kon_Latn",
    "Korean":"kor_Hang","Lao":"lao_Laoo","Ligurian":"lij_Latn",
    "Limburgish":"lim_Latn","Lingala":"lin_Latn","Lithuanian":"lit_Latn",
    "Lombard":"lmo_Latn","Latgalian":"ltg_Latn","Luxembourgish":"ltz_Latn",
    "Luba-Kasai":"lua_Latn","Ganda":"lug_Latn","Luo":"luo_Latn",
    "Mizo":"lus_Latn","Standard Latvian":"lvs_Latn","Magahi":"mag_Deva",
    "Maithili":"mai_Deva","Malayalam":"mal_Mlym","Marathi":"mar_Deva",
    "Minangkabau (Arabic script)":"min_Arab",
    "Minangkabau (Latin script)":"min_Latn","Macedonian":"mkd_Cyrl",
    "Plateau Malagasy":"plt_Latn","Maltese":"mlt_Latn",
    "Meitei (Bengali script)":"mni_Beng","Halh Mongolian":"khk_Cyrl",
    "Mossi":"mos_Latn","Maori":"mri_Latn","Burmese":"mya_Mymr",
    "Dutch":"nld_Latn","Norwegian Nynorsk":"nno_Latn",
    "Norwegian Bokmål":"nob_Latn","Nepali":"npi_Deva",
    "Northern Sotho":"nso_Latn","Nuer":"nus_Latn","Nyanja":"nya_Latn",
    "Occitan":"oci_Latn","West Central Oromo":"gaz_Latn","Odia":"ory_Orya",
    "Pangasinan":"pag_Latn","Eastern Panjabi":"pan_Guru",
    "Papiamento":"pap_Latn","Western Persian":"pes_Arab","Polish":"pol_Latn",
    "Portuguese":"por_Latn","Dari":"prs_Arab","Southern Pashto":"pbt_Arab",
    "Ayacucho Quechua":"quy_Latn","Romanian":"ron_Latn","Rundi":"run_Latn",
    "Russian":"rus_Cyrl","Sango":"sag_Latn","Sanskrit":"san_Deva",
    "Santali":"sat_Olck","Sicilian":"scn_Latn","Shan":"shn_Mymr",
    "Sinhala":"sin_Sinh","Slovak":"slk_Latn","Slovenian":"slv_Latn",
    "Samoan":"smo_Latn","Shona":"sna_Latn","Sindhi":"snd_Arab",
    "Somali":"som_Latn","Southern Sotho":"sot_Latn","Spanish":"spa_Latn",
    "Tosk Albanian":"als_Latn","Sardinian":"srd_Latn","Serbian":"srp_Cyrl",
    "Swati":"ssw_Latn","Sundanese":"sun_Latn","Swedish":"swe_Latn",
    "Swahili":"swh_Latn","Silesian":"szl_Latn","Tamil":"tam_Taml",
    "Tatar":"tat_Cyrl","Telugu":"tel_Telu","Tajik":"tgk_Cyrl",
    "Tagalog":"tgl_Latn","Thai":"tha_Thai","Tigrinya":"tir_Ethi",
    "Tamasheq (Latin script)":"taq_Latn",
    "Tamasheq (Tifinagh script)":"taq_Tfng","Tok Pisin":"tpi_Latn",
    "Tswana":"tsn_Latn","Tsonga":"tso_Latn","Turkmen":"tuk_Latn",
    "Tumbuka":"tum_Latn","Turkish":"tur_Latn","Twi":"twi_Latn",
    "Central Atlas Tamazight":"tzm_Tfng","Uyghur":"uig_Arab",
    "Ukrainian":"ukr_Cyrl","Umbundu":"umb_Latn","Urdu":"urd_Arab",
    "Northern Uzbek":"uzn_Latn","Venetian":"vec_Latn","Vietnamese":"vie_Latn",
    "Waray":"war_Latn","Wolof":"wol_Latn","Xhosa":"xho_Latn",
    "Eastern Yiddish":"ydd_Hebr","Yoruba":"yor_Latn","Yue Chinese":"yue_Hant",
    "Chinese (Simplified)":"zho_Hans","Chinese (Traditional)":"zho_Hant",
    "Standard Malay":"zsm_Latn","Zulu":"zul_Latn",
}
LANGUAGE_NAMES = sorted(LANGUAGES.keys())

# ─── Session state ─────────────────────────────────────────────────────────────
for k, v in {
    "src_lang":      DEFAULT_SRC_LANG,
    "tgt_lang":      DEFAULT_TGT_LANG,
    "translation":   "",
    "trans_pair":    "",
    "trans_via":     "",
    "whisper_heard": "",
    "last_audio_hash": "",   # prevents re-sending same audio on rerun
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-block">
    <h1>Translator</h1>
    <p>Whisper · NLLB-200-3.3B · Coqui XTTS v2 · Offline · Local</p>
</div>
""", unsafe_allow_html=True)

# ─── Health badge ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=30, show_spinner=False)
def check_health():
    try:
        r = requests.get(f"{API_BASE}/health", timeout=3)
        if r.status_code == 200:
            d = r.json()
            return True, d.get("device","cpu"), d.get("whisper",False), d.get("tts",False)
    except Exception:
        pass
    return False, None, False, False

online, dev, w_ok, tts_ok = check_health()
if online:
    parts = [f"● API ONLINE | {str(dev).upper()}"]
    if w_ok:  parts.append("WHISPER ✓")
    if tts_ok: parts.append("TTS ✓")
    st.markdown(
        f'<span class="badge badge-ok">{" | ".join(parts)}</span>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '<span class="badge badge-err">● API OFFLINE — run: uvicorn NLLB:app --reload</span>',
        unsafe_allow_html=True,
    )

# ─── Language row — native HTML selects + swap ─────────────────────────────────
def build_opts(selected_key):
    return "\n".join(
        f'<option value="{n}" {"selected" if n == st.session_state[selected_key] else ""}>{n}</option>'
        for n in LANGUAGE_NAMES
    )

st.markdown(f"""
<div class="lang-row">
    <div>
        <div class="field-label">From</div>
        <select class="native-select" id="sel-src"
                onchange="srcChange(this.value)">
            {build_opts('src_lang')}
        </select>
    </div>
    <div style="display:flex;align-items:flex-end;justify-content:center;">
        <div class="swap-circle" onclick="doSwap()" title="Swap">⇄</div>
    </div>
    <div>
        <div class="field-label">To</div>
        <select class="native-select" id="sel-tgt"
                onchange="tgtChange(this.value)">
            {build_opts('tgt_lang')}
        </select>
    </div>
</div>
<script>
function srcChange(v){{sessionStorage.setItem('__src',v);
    document.querySelector('[aria-label="__src_btn"]')?.click();}}
function tgtChange(v){{sessionStorage.setItem('__tgt',v);
    document.querySelector('[aria-label="__tgt_btn"]')?.click();}}
function doSwap(){{
    document.querySelector('[aria-label="__swap_btn"]')?.click();}}
</script>
""", unsafe_allow_html=True)

# Hidden Streamlit sync widgets
_c1, _c2, _c3 = st.columns(3)
with _c1:
    _src = st.selectbox("s", LANGUAGE_NAMES,
        index=LANGUAGE_NAMES.index(st.session_state.src_lang)
              if st.session_state.src_lang in LANGUAGE_NAMES else 0,
        key="__src_sel", label_visibility="collapsed")
with _c2:
    _tgt = st.selectbox("t", LANGUAGE_NAMES,
        index=LANGUAGE_NAMES.index(st.session_state.tgt_lang)
              if st.session_state.tgt_lang in LANGUAGE_NAMES else 0,
        key="__tgt_sel", label_visibility="collapsed")
with _c3:
    if st.button("⇄", key="__swap_sel", type="secondary"):
        st.session_state.src_lang, st.session_state.tgt_lang = (
            st.session_state.tgt_lang, st.session_state.src_lang)
        st.rerun()

if _src != st.session_state.src_lang:
    st.session_state.src_lang = _src; st.rerun()
if _tgt != st.session_state.tgt_lang:
    st.session_state.tgt_lang = _tgt; st.rerun()

# ─── Input card — textarea + mic button at the bottom ─────────────────────────
st.markdown('<div class="field-label" style="margin-top:0.4rem;">Input Text</div>',
            unsafe_allow_html=True)

st.markdown('<div class="input-card">', unsafe_allow_html=True)

input_text = st.text_area(
    "input", height=140,
    placeholder="Type text here  OR  use the mic below to speak…",
    label_visibility="collapsed", key="input_area",
)

# ── Mic bar ──
st.markdown('<div class="mic-bar">', unsafe_allow_html=True)
st.markdown(
    '<span class="mic-hint">🎤 Click mic · speak · click again to stop</span>',
    unsafe_allow_html=True,
)

audio_bytes = audio_recorder(
    text="",
    recording_color="#00e5ff",
    neutral_color="#555e80",
    icon_size="lg",
    pause_threshold=2.5,
    key="mic_recorder",
)
st.markdown('</div>', unsafe_allow_html=True)  # close mic-bar
st.markdown('</div>', unsafe_allow_html=True)  # close input-card

# char count
ccount = len(input_text)
warn   = ccount >= CHAR_WARN_AT
st.markdown(
    f'<p class="char-count {"char-warn" if warn else ""}">'
    f'{ccount:,} / {CHAR_LIMIT:,} characters'
    f'{"  ⚠ near limit" if warn else ""}</p>',
    unsafe_allow_html=True,
)

# ── Show recorded audio preview + translate button ────────────────────────────
# audio_recorder returns bytes on EVERY render after recording.
# We use a hash to detect NEW recordings only — prevents infinite loop.
import hashlib

if audio_bytes is not None:
    audio_hash = hashlib.md5(audio_bytes).hexdigest()
    is_new_recording = (audio_hash != st.session_state.last_audio_hash)

    if is_new_recording:
        # Show preview so user knows recording was captured
        st.markdown(
            '<div class="field-label" style="margin-top:0.6rem;">🎤 Recording captured</div>',
            unsafe_allow_html=True,
        )
        st.audio(audio_bytes, format="audio/wav")

        # Single button to trigger pipeline — user controls when it fires
        if st.button("▶ TRANSLATE VOICE →", key="voice_translate_btn"):
            st.session_state.last_audio_hash = audio_hash
            tgt_code = LANGUAGES[st.session_state.tgt_lang]

            # Show step-by-step progress
            status = st.empty()
            status.markdown(
                '<p style="font-family:IBM Plex Mono,monospace;font-size:0.8rem;color:#00e5ff;">' +
                '⚙️ Step 1/3 — Whisper transcribing…</p>',
                unsafe_allow_html=True,
            )

            try:
                resp = requests.post(
                    f"{API_BASE}/voice-translate",
                    files={"audio": ("recording.wav", audio_bytes, "audio/wav")},
                    data={"target_lang": tgt_code},
                    timeout=600,   # 10 min — enough for any CPU
                )

                status.empty()

                if resp.status_code == 200:
                    headers    = resp.headers
                    heard      = headers.get("X-Transcribed", "")
                    translated = headers.get("X-Translated",  "")
                    detected   = headers.get("X-Detected-Lang", "")

                    st.session_state.translation   = translated
                    st.session_state.trans_pair    = f"🎤 Voice ({detected}) → {st.session_state.tgt_lang}"
                    st.session_state.trans_via     = "Whisper → NLLB → Coqui TTS"
                    st.session_state.whisper_heard = heard
                    st.session_state.last_wav      = resp.content
                    st.rerun()
                else:
                    try:    detail = resp.json().get("detail", "Unknown")
                    except: detail = resp.text
                    st.error(f"Voice error {resp.status_code}: {detail}")

            except requests.exceptions.Timeout:
                st.error(
                    "⏳ Request timed out after 10 minutes. "
                    "Try a shorter recording or switch to smaller models."
                )
            except requests.exceptions.ConnectionError:
                st.error("Cannot reach API. Run: `uvicorn NLLB:app --reload`")
            except Exception as e:
                st.error(f"Voice error: {e}")

# ─── Translate button (text) ───────────────────────────────────────────────────
translate_clicked = st.button("TRANSLATE →", key="translate_btn")

# ─── Text translation logic ────────────────────────────────────────────────────
if translate_clicked:
    text = input_text.strip()
    if not text:
        st.warning("Please enter some text.")
    elif st.session_state.src_lang == st.session_state.tgt_lang:
        st.warning("Source and target languages are the same.")
    elif ccount > CHAR_LIMIT:
        st.error(f"Text exceeds {CHAR_LIMIT:,} characters.")
    else:
        src_code = LANGUAGES[st.session_state.src_lang]
        tgt_code = LANGUAGES[st.session_state.tgt_lang]
        with st.spinner("Translating…"):
            try:
                resp = requests.post(
                    f"{API_BASE}/translate",
                    json={"text": text,
                          "source_lang": src_code,
                          "target_lang": tgt_code},
                    timeout=180,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    st.session_state.translation   = data["translated_text"]
                    st.session_state.trans_pair    = f"{st.session_state.src_lang} → {st.session_state.tgt_lang}"
                    st.session_state.trans_via     = "NLLB-200-3.3B"
                    st.session_state.whisper_heard = ""
                    st.rerun()
                else:
                    st.error(f"Error {resp.status_code}: {resp.json().get('detail','Unknown')}")
            except requests.exceptions.ConnectionError:
                st.error("Cannot reach API. Run: `uvicorn NLLB:app --reload`")
            except Exception as e:
                st.error(f"Error: {e}")

# ─── Output ───────────────────────────────────────────────────────────────────
if st.session_state.translation:
    st.markdown("---")

    # Show what Whisper heard (only for voice translations)
    if st.session_state.whisper_heard:
        st.markdown(
            f'<div class="whisper-box">'
            f'🎤 Whisper heard: <span>{st.session_state.whisper_heard}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<div class="field-label">Translation &nbsp;·&nbsp; {st.session_state.trans_pair}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="output-tag">via {st.session_state.trans_via}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="output-box">{st.session_state.translation}</div>',
        unsafe_allow_html=True,
    )

    # Play spoken audio — use saved WAV from session state
    if st.session_state.trans_via == "Whisper → NLLB → Coqui TTS":
        wav = st.session_state.get("last_wav", b"")
        if wav:
            st.markdown(
                '<div class="field-label" style="margin-top:0.8rem;">🔊 Spoken Translation</div>',
                unsafe_allow_html=True,
            )
            st.audio(wav, format="audio/wav")

    st.code(st.session_state.translation, language=None)

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<p style="text-align:center;color:#3a4060;'
    'font-family:\'IBM Plex Mono\',monospace;font-size:0.72rem;">'
    'Whisper large-v3-turbo · NLLB-200-3.3B · Coqui XTTS v2 · '
    'Meta AI + OpenAI + Coqui · 100% Local · No data leaves your machine'
    '</p>',
    unsafe_allow_html=True,
)