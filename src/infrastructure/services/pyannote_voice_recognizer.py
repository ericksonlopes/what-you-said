import os
import time
from pathlib import Path
import numpy as np
from src.domain.entities.voice import MatchResult, BatchResult
from src.infrastructure.utils.audio_utils import (
    load_audio_tensor,
    cosine_similarity,
    get_best_device,
)


class VoiceRecognizer:
    def __init__(self, voice_db, hf_token: str, threshold: float = 0.8):
        self.voice_db = voice_db
        self.hf_token = hf_token
        self.threshold = threshold
        self._device = get_best_device()
        self._inference = None

    def _get_inference(self):
        if self._inference is None:
            from pyannote.audio import Model, Inference
            import torch

            model = Model.from_pretrained(
                "pyannote/wespeaker-voxceleb-resnet34-LM", use_auth_token=self.hf_token
            )
            device = torch.device(self._device)
            self._inference = Inference(model, window="whole", device=device)
        return self._inference

    def _compare(self, embedding: np.ndarray) -> list[tuple[str, float, str]]:
        scores = []
        for name, info in self.voice_db.voices.items():
            ref_emb = np.array(info["embedding"])
            voice_id = info["id"]
            sim = cosine_similarity(embedding, ref_emb)
            scores.append((name, sim, voice_id))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    def identify(self, audio_path: str) -> MatchResult:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"File not found: {audio_path}")
        if len(self.voice_db) == 0:
            raise ValueError("Voice database is empty.")

        t0 = time.time()
        inference = self._get_inference()
        audio_tensor = load_audio_tensor(audio_path)
        input_emb = inference(audio_tensor)
        scores = self._compare(input_emb)
        elapsed = time.time() - t0

        return MatchResult(
            audio_path=audio_path,
            scores=scores,
            threshold=self.threshold,
            elapsed=elapsed,
        )

    def identify_dir(self, audio_dir: str) -> BatchResult:
        if not os.path.isdir(audio_dir):
            raise NotADirectoryError(f"Folder not found: {audio_dir}")

        AUDIO_EXTENSIONS = {"*.wav", "*.mp3", "*.m4a", "*.flac", "*.ogg", "*.opus"}
        audio_files: list[Path] = []
        for ext in AUDIO_EXTENSIONS:
            audio_files.extend(Path(audio_dir).glob(ext))
        audio_files.sort(key=lambda p: p.name)

        if not audio_files:
            raise FileNotFoundError(f"No audio files found in: {audio_dir}")
        if len(self.voice_db) == 0:
            raise ValueError("Voice database is empty.")

        t0 = time.time()
        inference = self._get_inference()
        results = {}
        for audio_path in audio_files:
            audio_tensor = load_audio_tensor(str(audio_path))
            input_emb = inference(audio_tensor)
            scores = self._compare(input_emb)
            results[audio_path.stem] = MatchResult(
                audio_path=str(audio_path),
                scores=scores,
                threshold=self.threshold,
            )
        elapsed = time.time() - t0
        return BatchResult(results=results, elapsed=elapsed)
