from enum import Enum


class DiarizationStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    AWAITING_VERIFICATION = "awaiting_verification"


class DiarizationStep(Enum):
    STARTING = "starting"
    DOWNLOADING = "downloading"
    DIARIZING = "diarizing"
    EXPORTING = "exporting"
    RECOGNIZING = "recognizing"
