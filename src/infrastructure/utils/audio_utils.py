import os
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

try:
    from pydub import AudioSegment

    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

TARGET_SAMPLE_RATE = 16_000


def load_audio_tensor(audio_path: str) -> dict:
    path = Path(audio_path)
    tmp_wav = None

    if path.suffix.lower() not in {".wav", ".flac", ".ogg", ".opus"}:
        if not PYDUB_AVAILABLE:
            raise ImportError(f"To load '{path.suffix}' install pydub: pip install pydub")
        tmp_wav = str(path.with_suffix(".tmp_utils.wav"))
        AudioSegment.from_file(audio_path).export(tmp_wav, format="wav")
        read_path = tmp_wav
    else:
        read_path = audio_path

    try:
        data, sr = sf.read(read_path, dtype="float32", always_2d=True)
    finally:
        if tmp_wav and os.path.exists(tmp_wav):
            os.remove(tmp_wav)

    waveform = torch.from_numpy(data.T)

    if sr != TARGET_SAMPLE_RATE:
        import torchaudio.functional as F

        waveform = F.resample(waveform, sr, TARGET_SAMPLE_RATE)

    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)

    return {"waveform": waveform, "sample_rate": TARGET_SAMPLE_RATE}


def load_whisperx_audio(audio_path: str) -> np.ndarray:
    d = load_audio_tensor(audio_path)
    return d["waveform"].squeeze(0).numpy()


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def get_best_device() -> str:
    """Retorna 'cuda' se disponível, senão 'cpu'."""
    return "cuda" if torch.cuda.is_available() else "cpu"
