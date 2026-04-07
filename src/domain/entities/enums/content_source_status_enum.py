from enum import Enum


class ContentSourceStatus(Enum):
    ACTIVE = "active"
    DEACTIVE = "deactive"
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"
    AWAITING_VERIFICATION = "awaiting_verification"
