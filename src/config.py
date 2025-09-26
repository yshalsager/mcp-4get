"""Configuration handling for the 4get MCP server."""

from __future__ import annotations

from os import environ
from dataclasses import dataclass
from typing import TypeVar
from urllib.parse import urlparse

from src import __version__

DEFAULT_BASE_URL = 'https://4get.ca'
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_CACHE_TTL_SECONDS = 600.0
DEFAULT_CACHE_MAXSIZE = 128
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BASE_DELAY = 1.0
DEFAULT_RETRY_MAX_DELAY = 60.0
DEFAULT_CONNECTION_POOL_MAXSIZE = 10
DEFAULT_CONNECTION_POOL_MAX_KEEPALIVE = 5


@dataclass(slots=True)
class Config:
    """Configuration settings for the 4get MCP server.

    This class encapsulates all configuration options with sensible defaults.
    Values can be customized via environment variables or direct instantiation.

    Environment Variables:
        FOURGET_BASE_URL: Base URL of the 4get instance (default: https://4get.ca)
        FOURGET_PASS: Optional pass token for rate-limited instances
        FOURGET_USER_AGENT: Custom User-Agent header
        FOURGET_TIMEOUT: Request timeout in seconds (default: 20.0)
        FOURGET_CACHE_TTL: Cache lifetime in seconds (default: 600.0)
        FOURGET_CACHE_MAXSIZE: Maximum cached responses (default: 128)
        FOURGET_MAX_RETRIES: Maximum retry attempts (default: 3)
        FOURGET_RETRY_BASE_DELAY: Base retry delay in seconds (default: 1.0)
        FOURGET_RETRY_MAX_DELAY: Maximum retry delay in seconds (default: 60.0)
        FOURGET_CONNECTION_POOL_MAXSIZE: Max concurrent connections (default: 10)
        FOURGET_CONNECTION_POOL_MAX_KEEPALIVE: Max persistent connections (default: 5)

    Example:
        >>> # Use environment variables
        >>> config = Config.from_env()
        >>>
        >>> # Or configure directly
        >>> config = Config(
        >>>     base_url="https://my-4get-instance.com",
        >>>     pass_token="my-secret-token",
        >>>     timeout=30.0,
        >>>     max_retries=5
        >>> )
    """

    base_url: str = DEFAULT_BASE_URL
    pass_token: str | None = None
    user_agent: str = f'mcp-4get/{__version__}'
    timeout: float = DEFAULT_TIMEOUT_SECONDS
    cache_ttl: float = DEFAULT_CACHE_TTL_SECONDS
    cache_maxsize: int = DEFAULT_CACHE_MAXSIZE
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_base_delay: float = DEFAULT_RETRY_BASE_DELAY
    retry_max_delay: float = DEFAULT_RETRY_MAX_DELAY
    connection_pool_maxsize: int = DEFAULT_CONNECTION_POOL_MAXSIZE
    connection_pool_max_keepalive: int = DEFAULT_CONNECTION_POOL_MAX_KEEPALIVE

    @classmethod
    def from_env(cls) -> Config:
        """Create a configuration instance from environment variables.

        Reads configuration values from environment variables with fallback
        to sensible defaults. All numeric values are validated for correctness.

        Returns:
            Validated Config instance with values from environment or defaults.

        Raises:
            ValueError: If any configuration value is invalid.

        Example:
            >>> from os import environ
            >>> environ['FOURGET_TIMEOUT'] = '30.0'
            >>> environ['FOURGET_MAX_RETRIES'] = '5'
            >>> config = Config.from_env()
            >>> print(f"Timeout: {config.timeout}s, Retries: {config.max_retries}")
        """

        base_url = environ.get('FOURGET_BASE_URL', DEFAULT_BASE_URL).rstrip('/')
        pass_token = environ.get('FOURGET_PASS')

        user_agent = environ.get('FOURGET_USER_AGENT') or f'mcp-4get/{__version__}'

        timeout = _read_number('FOURGET_TIMEOUT', float, DEFAULT_TIMEOUT_SECONDS)
        cache_ttl = _read_number('FOURGET_CACHE_TTL', float, DEFAULT_CACHE_TTL_SECONDS)
        cache_maxsize = int(
            _read_number('FOURGET_CACHE_MAXSIZE', int, DEFAULT_CACHE_MAXSIZE, minimum=1)
        )
        max_retries = int(_read_number('FOURGET_MAX_RETRIES', int, DEFAULT_MAX_RETRIES, minimum=0))
        retry_base_delay = _read_number(
            'FOURGET_RETRY_BASE_DELAY', float, DEFAULT_RETRY_BASE_DELAY, minimum=0.1
        )
        retry_max_delay = _read_number(
            'FOURGET_RETRY_MAX_DELAY', float, DEFAULT_RETRY_MAX_DELAY, minimum=1.0
        )
        connection_pool_maxsize = int(
            _read_number(
                'FOURGET_CONNECTION_POOL_MAXSIZE', int, DEFAULT_CONNECTION_POOL_MAXSIZE, minimum=1
            )
        )
        connection_pool_max_keepalive = int(
            _read_number(
                'FOURGET_CONNECTION_POOL_MAX_KEEPALIVE',
                int,
                DEFAULT_CONNECTION_POOL_MAX_KEEPALIVE,
                minimum=1,
            )
        )

        return cls(
            base_url=base_url,
            pass_token=pass_token,
            user_agent=user_agent,
            timeout=timeout,
            cache_ttl=cache_ttl,
            cache_maxsize=cache_maxsize,
            max_retries=max_retries,
            retry_base_delay=retry_base_delay,
            retry_max_delay=retry_max_delay,
            connection_pool_maxsize=connection_pool_maxsize,
            connection_pool_max_keepalive=connection_pool_max_keepalive,
        )._validate()

    def _validate(self) -> Config:
        """Validate all configuration values for correctness.

        Performs comprehensive validation including:
        - URL format validation
        - Numeric range validation
        - Logical consistency checks

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If any configuration value is invalid with descriptive message.
        """
        # Validate base_url is a valid URL
        parsed = urlparse(self.base_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f'Invalid base_url: {self.base_url}')
        if parsed.scheme not in ('http', 'https'):
            raise ValueError(f'base_url must use http or https scheme: {self.base_url}')

        # Validate numeric ranges
        if self.timeout <= 0:
            raise ValueError(f'timeout must be positive: {self.timeout}')
        if self.cache_ttl < 0:
            raise ValueError(f'cache_ttl must be non-negative: {self.cache_ttl}')
        if self.cache_maxsize < 1:
            raise ValueError(f'cache_maxsize must be at least 1: {self.cache_maxsize}')
        if self.max_retries < 0:
            raise ValueError(f'max_retries must be non-negative: {self.max_retries}')
        if self.retry_base_delay <= 0:
            raise ValueError(f'retry_base_delay must be positive: {self.retry_base_delay}')
        if self.retry_max_delay <= 0:
            raise ValueError(f'retry_max_delay must be positive: {self.retry_max_delay}')
        if self.retry_base_delay > self.retry_max_delay:
            raise ValueError(
                f'retry_base_delay ({self.retry_base_delay}) must not exceed '
                f'retry_max_delay ({self.retry_max_delay})'
            )
        if self.connection_pool_maxsize < 1:
            raise ValueError(
                f'connection_pool_maxsize must be at least 1: {self.connection_pool_maxsize}'
            )
        if self.connection_pool_max_keepalive < 1:
            raise ValueError(
                f'connection_pool_max_keepalive must be at least 1: {self.connection_pool_max_keepalive}'
            )
        if self.connection_pool_max_keepalive > self.connection_pool_maxsize:
            raise ValueError(
                f'connection_pool_max_keepalive ({self.connection_pool_max_keepalive}) must not exceed '
                f'connection_pool_maxsize ({self.connection_pool_maxsize})'
            )

        return self


T = TypeVar('T', bound=float | int)


def _read_number(
    name: str,
    cast: type[T],
    default: T,
    *,
    minimum: T | None = None,
) -> T:
    raw = environ.get(name)
    if not raw:
        return default
    try:
        value = cast(raw)
    except (TypeError, ValueError):
        return default
    if minimum is not None and value < minimum:
        return default
    return value
