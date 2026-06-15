# save as download_tts.py and run it once
from TTS.api import TTS

# This downloads the best multilingual TTS model (~1.8GB)
# It saves automatically to: C:\Users\shilob.das\AppData\Local\tts\
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
print("✅ Coqui XTTS v2 downloaded successfully!")