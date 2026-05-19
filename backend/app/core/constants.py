from enum import StrEnum


class Sentiment(StrEnum):
    POSITIVE = "Positive"
    NEUTRAL = "Neutral"
    NEGATIVE = "Negative"


class ChurnRisk(StrEnum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class ProcessingStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class WebSocketEvent(StrEnum):
    RECEIVED = "received"
    PREPROCESSING = "preprocessing"
    LOCAL_ML = "local_ml"
    OPENAI_PROCESSING = "openai_processing"
    VALIDATING = "validating"
    SAVED = "saved"
    FAILED = "failed"
