from enum import StrEnum


EMBEDDING_DIMENSIONS = 384
MIN_AI_CONFIDENCE = 0.35
HIGH_URGENCY_REVIEW_THRESHOLD = 70
MIN_DRAFT_RESPONSE_WORDS = 8
MIN_NEXT_ACTION_WORDS = 3
MAX_PROMPT_NARRATIVE_CHARS = 6000
MAX_PROMPT_EVIDENCE_TEXT_CHARS = 500


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
    HUMAN_REVIEW = "human_review"
    FAILED = "failed"


class WebSocketEvent(StrEnum):
    RECEIVED = "received"
    PREPROCESSING = "preprocessing"
    LOCAL_ML = "local_ml"
    BEDROCK_PROCESSING = "bedrock_processing"
    VALIDATING = "validating"
    SAVED = "saved"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    FAILED = "failed"


class ReviewReason(StrEnum):
    LOW_CONFIDENCE = "low_confidence"
    WEAK_DRAFT_RESPONSE = "weak_draft_response"
    VAGUE_NEXT_ACTION = "vague_next_action"
    BEDROCK_UNAVAILABLE_AFTER_RETRIES = "bedrock_unavailable_after_retries"
    HIGH_RISK_HIGH_URGENCY = "high_risk_high_urgency"
    INVALID_AI_OUTPUT = "invalid_ai_output"


class ProcessingTrigger(StrEnum):
    API_REQUEST = "api_request"
    IMPORTED_REQUEST = "imported_request"
    REVIEW_RERUN = "review_rerun"
    BATCH_PROCESSING = "batch_processing"


class Role(StrEnum):
    AGENT = "agent"
    MANAGER = "manager"
    ADMIN = "admin"


class JobType(StrEnum):
    PROCESS_COMPLAINTS = "process_complaints"
    EMBEDDING_BACKFILL = "embedding_backfill"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


class JobItemStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    HUMAN_REVIEW = "human_review"
    FAILED = "failed"
