class IvdError(RuntimeError):
    """Base error for user-facing CLI failures."""


class ConfigError(IvdError):
    """Raised when required configuration is missing."""


class AudioError(IvdError):
    """Raised when audio probing or conversion fails."""


class ApiError(IvdError):
    """Raised when an external API call fails."""
