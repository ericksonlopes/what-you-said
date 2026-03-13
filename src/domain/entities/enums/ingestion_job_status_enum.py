from enum import Enum


class IngestionJobStatus(Enum):
    STARTED = "started"
    PROCESSING = "processing"
    FINISHED = "finished"
    FAILED = "failed"
    CANCELLED = "cancelled"
