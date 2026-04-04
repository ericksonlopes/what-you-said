import logging
import os

import numpy as np
import torch
import whisperx

from src.domain.entities.diarization import Segment, DiarizationResult
from src.infrastructure.utils.audio_utils import load_whisperx_audio, get_best_device

logger = logging.getLogger(__name__)

# Global torch configuration to avoid RuntimeError: "set_num_threads is not allowed after parallel work has started"
_device_type = get_best_device()
if _device_type == "cpu":
    _cpu_count = os.cpu_count() or 4
    try:
        torch.set_num_threads(_cpu_count)
        torch.set_num_interop_threads(max(1, _cpu_count // 2))
        logger.info("Global torch CPU config: threads=%d", _cpu_count)
    except RuntimeError:
        # Already set or parallel work started
        pass


class AudioDiarizer:
    def __init__(
        self,
        hf_token: str,
        model_size: str = "large-v2",
        batch_size: int = 16,
    ):
        self.hf_token = hf_token
        self.model_size = model_size
        self._device = _device_type
        self._compute_type = "float16" if self._device == "cuda" else "int8"

        if self._device == "cpu":
            # batch_size=1 is more efficient on CPU (avoids memory thrashing)
            self.batch_size = 1
            logger.info("CPU mode enabled: batch_size=1")
        else:
            self.batch_size = batch_size

    def _transcribe(
        self, audio_path: str, language: str | None
    ) -> tuple[dict, np.ndarray]:
        logger.info(
            "[1/3] Transcription starting (model=%s, device=%s, compute=%s)",
            self.model_size,
            self._device,
            self._compute_type,
        )
        audio = load_whisperx_audio(audio_path)
        logger.info("[1/3] Audio loaded, shape=%s", audio.shape)

        logger.info("[1/3] Loading whisperx model...")
        model = whisperx.load_model(
            self.model_size,
            self._device,
            compute_type=self._compute_type,
            language=language,
        )
        logger.info(
            "[1/3] Model loaded, starting transcription (batch_size=%d)...",
            self.batch_size,
        )

        result = model.transcribe(audio, batch_size=self.batch_size)
        logger.info(
            "[1/3] Transcription complete: %d segments, language=%s",
            len(result.get("segments", [])),
            result.get("language", "?"),
        )

        del model
        if self._device == "cuda":
            torch.cuda.empty_cache()
        return result, audio

    def _align(self, result: dict, audio: np.ndarray, language: str | None) -> dict:
        logger.info("[2/3] Word alignment starting")
        lang = language or result.get("language", "en")
        try:
            model_a, metadata = whisperx.load_align_model(
                language_code=lang, device=self._device
            )
            result = whisperx.align(
                result["segments"],
                model_a,
                metadata,
                audio,
                self._device,
                return_char_alignments=False,
            )
            del model_a
            if self._device == "cuda":
                torch.cuda.empty_cache()
            logger.info("[2/3] Alignment complete")
        except Exception as e:
            logger.warning("[2/3] Skipped alignment: %s", e)
        return result

    def _diarize(
        self,
        audio_path: str,
        result: dict,
        num_speakers: int | None,
        min_speakers: int | None,
        max_speakers: int | None,
    ) -> tuple[list[Segment], str]:
        logger.info("[3/3] Speaker diarization starting")
        kwargs = {}
        if num_speakers:
            kwargs["num_speakers"] = num_speakers
        else:
            if min_speakers:
                kwargs["min_speakers"] = min_speakers
            if max_speakers:
                kwargs["max_speakers"] = max_speakers

        audio_np = load_whisperx_audio(audio_path)
        logger.info("[3/3] Loading diarization pipeline...")
        from whisperx.diarize import DiarizationPipeline

        diarize_model = DiarizationPipeline(
            model_name="pyannote/speaker-diarization-3.1",
            token=self.hf_token,
            device=self._device,
        )
        logger.info("[3/3] Running diarization with kwargs=%s...", kwargs)
        diarize_segments = diarize_model(audio_np, **kwargs)
        result = whisperx.assign_word_speakers(diarize_segments, result)

        segments = [
            Segment.create(
                speaker=seg.get("speaker", "UNKNOWN"),
                start=round(seg["start"], 3),
                end=round(seg["end"], 3),
                text=seg["text"].strip(),
            )
            for seg in result["segments"]
        ]
        logger.info("[3/3] Diarization complete: %d segments", len(segments))
        return segments, result.get("language", "?")

    def run(
        self,
        audio_path: str,
        language: str | None = None,
        num_speakers: int | None = None,
        min_speakers: int | None = None,
        max_speakers: int | None = None,
    ) -> DiarizationResult:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"File not found: {audio_path}")

        logger.info("Starting diarization pipeline for: %s", audio_path)
        result_trans, audio = self._transcribe(audio_path, language)
        result_aligned = self._align(result_trans, audio, language)
        segments, lang = self._diarize(
            audio_path, result_aligned, num_speakers, min_speakers, max_speakers
        )

        return DiarizationResult(
            segments=segments,
            language=language or lang,
            audio_path=audio_path,
        )
