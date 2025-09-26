"""Custom exception hierarchy for 4get client errors."""

from __future__ import annotations


class FourGetError(Exception):
    """Base exception for 4get client failures."""


class FourGetAuthError(FourGetError):
    """Raised when authentication or rate limiting errors occur."""


class FourGetAPIError(FourGetError):
    """Raised when the 4get API returns a non-success status value."""

    def __init__(self, status: str, message: str | None = None) -> None:
        self.status = status
        self.message = message
        if message:
            super().__init__(f'status={status}: {message}')
        else:
            super().__init__(f'status={status}')


class FourGetTransportError(FourGetError):
    """Raised when network or protocol-level failures occur."""

    def __init__(self, original: Exception) -> None:
        self.original = original
        super().__init__(str(original))
