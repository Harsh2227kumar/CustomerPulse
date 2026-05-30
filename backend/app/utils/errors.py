class CustomerPulseError(Exception):
    """Base application error for expected backend failures."""


class AIValidationError(CustomerPulseError):
    """Raised when AI output cannot be trusted or parsed."""
