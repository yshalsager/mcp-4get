"""Async HTTP client for the 4get meta search API."""

from __future__ import annotations

import asyncio
import random
from enum import Enum
from typing import Any, Mapping

import httpx

from src.cache import TTLCache
from src.config import Config
from src.errors import (
    FourGetAPIError,
    FourGetAuthError,
    FourGetError,
    FourGetTransportError,
)


class FourGetClient:
    """Async HTTP client for the 4get meta search API.

    This client provides a convenient interface to the 4get search engine API,
    with built-in caching, retry logic, and error handling.

    Features:
    - Exponential backoff retry for rate-limited and network errors
    - TTL-based response caching to respect API rate limits
    - Connection pooling for optimal performance
    - Comprehensive error handling with custom exception types

    Example:
        >>> config = Config.from_env()
        >>> client = FourGetClient(config)
        >>>
        >>> # Basic web search
        >>> result = await client.web_search("python programming")
        >>> print(f"Found {len(result['web'])} results")
        >>>
        >>> # Paginated search
        >>> if result.get('npt'):
        >>>     next_page = await client.web_search(
        >>>         "ignored", page_token=result['npt']
        >>>     )
        >>>
        >>> # Extended search with options
        >>> result = await client.web_search(
        >>>     "machine learning",
        >>>     extended_search=True,
        >>>     options={'lang': 'en', 'country': 'us'}
        >>> )
    """

    def __init__(
        self,
        config: Config,
        *,
        cache: TTLCache | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._config = config
        self._cache = cache or TTLCache(config.cache_ttl, config.cache_maxsize)
        self._transport = transport

    async def web_search(
        self,
        query: str,
        *,
        page_token: str | None = None,
        extended_search: bool | None = None,
        options: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform a web search using the 4get API.

        Args:
            query: Search query string. Ignored when using page_token.
            page_token: Pagination token from previous response's 'npt' field.
            extended_search: Enable extended search for more comprehensive results.
            options: Additional search parameters (e.g., language, region).

        Returns:
            Search response containing:
            - status: "ok" for successful requests
            - web: List of web search results with title, url, description
            - npt: Next page token for pagination (if available)
            - answer: Featured answer/snippet (if available)
            - spelling: Spelling correction info
            - related: List of related search terms

        Raises:
            FourGetAuthError: Rate limited or invalid authentication
            FourGetAPIError: API returned non-success status
            FourGetTransportError: Network or HTTP protocol errors
            FourGetError: Generic client errors

        Example:
            >>> result = await client.web_search("model context protocol")
            >>> for item in result['web']:
            >>>     print(f"{item['title']}: {item['url']}")
        """
        return await self._call_search(
            'web',
            query,
            page_token=page_token,
            options=options,
            include_extended=extended_search,
        )

    async def image_search(
        self,
        query: str,
        *,
        page_token: str | None = None,
        options: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Search for images using the 4get API.

        Args:
            query: Image search query. Ignored when using page_token.
            page_token: Pagination token from previous response's 'npt' field.
            options: Additional parameters like size, color, type filters.

        Returns:
            Image search response containing:
            - status: "ok" for successful requests
            - image: List of image results with url, title, thumb info
            - npt: Next page token for pagination (if available)

        Raises:
            FourGetAuthError: Rate limited or invalid authentication
            FourGetAPIError: API returned non-success status
            FourGetTransportError: Network or HTTP protocol errors

        Example:
            >>> result = await client.image_search("python logo")
            >>> for img in result.get('image', []):
            >>>     print(f"Image: {img['url']}")
        """
        return await self._call_search('images', query, page_token=page_token, options=options)

    async def news_search(
        self,
        query: str,
        *,
        page_token: str | None = None,
        options: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Search for news articles using the 4get API.

        Args:
            query: News search query. Ignored when using page_token.
            page_token: Pagination token from previous response's 'npt' field.
            options: Additional parameters like date range, source filters.

        Returns:
            News search response containing:
            - status: "ok" for successful requests
            - news: List of news articles with title, url, description, date
            - npt: Next page token for pagination (if available)

        Raises:
            FourGetAuthError: Rate limited or invalid authentication
            FourGetAPIError: API returned non-success status
            FourGetTransportError: Network or HTTP protocol errors

        Example:
            >>> result = await client.news_search("artificial intelligence")
            >>> for article in result.get('news', []):
            >>>     print(f"{article['title']} - {article['date']}")
        """
        return await self._call_search('news', query, page_token=page_token, options=options)

    async def _call_search(
        self,
        endpoint: str,
        query: str,
        *,
        page_token: str | None,
        options: Mapping[str, Any] | None,
        include_extended: bool | None = None,
    ) -> dict[str, Any]:
        params = self._prepare_search_params(query, page_token, options)
        if include_extended is not None:
            params['extendedsearch'] = include_extended
        return await self._search(endpoint, params)

    async def _search(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        normalized_params = self._normalize_params(params)
        cache_key = self._cache_key(endpoint, normalized_params)
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached

        payload = await self._request(endpoint, normalized_params)
        await self._cache.set(cache_key, payload)
        return payload

    async def _request(self, endpoint: str, params: Mapping[str, Any]) -> dict[str, Any]:
        """Make HTTP request with exponential backoff retry logic."""
        url_path = f'/api/v1/{endpoint}'
        headers = {
            'User-Agent': self._config.user_agent,
            'Accept': 'application/json',
        }
        cookies = {'pass': self._config.pass_token} if self._config.pass_token else None

        last_exception = None

        # Configure connection limits for the client
        limits = httpx.Limits(
            max_connections=self._config.connection_pool_maxsize,
            max_keepalive_connections=self._config.connection_pool_max_keepalive,
        )

        for attempt in range(self._config.max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    base_url=self._config.base_url,
                    headers=headers,
                    cookies=cookies,
                    timeout=self._config.timeout,
                    transport=self._transport,
                    limits=limits,
                ) as client:
                    response = await client.get(url_path, params=params)
                    response.raise_for_status()

                    try:
                        data = response.json()
                    except ValueError as exc:
                        raise FourGetTransportError(exc) from exc

                    api_status = data.get('status')
                    if api_status is None:
                        raise FourGetError("Missing 'status' field in 4get response")
                    if api_status != 'ok':
                        message = data.get('message') or data.get('error') or data.get('detail')
                        raise FourGetAPIError(api_status, message)

                    return data

            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                if status_code == 429:
                    # Rate limited - this is retryable
                    last_exception = FourGetAuthError('Rate limited or invalid pass token')
                    if attempt < self._config.max_retries:
                        delay = self._calculate_backoff_delay(attempt)
                        await asyncio.sleep(delay)
                        continue
                    raise last_exception from exc
                else:
                    # Non-retryable HTTP error
                    raise FourGetTransportError(exc) from exc

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                # Network errors are retryable
                last_exception = FourGetTransportError(exc)
                if attempt < self._config.max_retries:
                    delay = self._calculate_backoff_delay(attempt)
                    await asyncio.sleep(delay)
                    continue
                raise last_exception from exc

            except httpx.HTTPError as exc:
                # Other HTTP errors are not retryable
                raise FourGetTransportError(exc) from exc

        # This should never be reached, but just in case
        if last_exception:
            raise last_exception
        raise FourGetError('Unexpected error in retry loop')

    @staticmethod
    def _prepare_search_params(
        query: str,
        page_token: str | None,
        options: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {'npt': page_token} if page_token else {'s': query}
        if options:
            params.update({key: value for key, value in options.items() if value is not None})
        return params

    @staticmethod
    def _normalize_params(params: Mapping[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, Enum):
                value = value.value
            if isinstance(value, bool):
                value = 'true' if value else 'false'
            normalized[key] = value
        return normalized

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter."""
        # Exponential backoff: base_delay * (2 ^ attempt)
        delay = self._config.retry_base_delay * (2**attempt)

        # Cap the delay at max_delay
        delay = min(delay, self._config.retry_max_delay)

        # Add jitter (±25% randomization)
        jitter = delay * 0.25 * (2 * random.random() - 1)
        delay += jitter

        # Ensure delay is never negative
        return max(0.1, delay)

    @staticmethod
    def _cache_key(endpoint: str, params: Mapping[str, Any]) -> str:
        query = httpx.QueryParams(params)
        serialized = tuple(query.multi_items())
        return f'{endpoint}:{serialized}'
