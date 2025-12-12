"""Custom exceptions for lifecycle tracking."""


class BlockingError(Exception):
    """Raised to block operation and show error to agent (exit code 2)."""
    pass


class NonBlockingError(Exception):
    """Raised to log error but allow operation to continue (exit code 1)."""
    pass
