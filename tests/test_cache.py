"""Comprehensive cache behavior and expiration tests."""

from __future__ import annotations

import asyncio
import time

import httpx
import pytest

from src.cache import CacheEntry, TTLCache
from src.client import FourGetClient
from src.config import Config

pytestmark = pytest.mark.asyncio


class TestTTLCache:
    """Test cache implementation in isolation."""

    async def test_cache_entry_expiration(self) -> None:
        """Test CacheEntry expiration logic."""
        entry = CacheEntry(value='test', expires_at=time.monotonic() + 1.0)

        # Should not be expired initially
        assert not entry.expired()

        # Should not be expired with explicit current time
        now = time.monotonic()
        assert not entry.expired(now)

        # Should be expired in the future
        future_time = time.monotonic() + 2.0
        assert entry.expired(future_time)

    async def test_cache_basic_operations(self) -> None:
        """Test basic cache set/get operations."""
        cache = TTLCache(ttl_seconds=1.0, maxsize=3)

        # Initially empty
        assert await cache.get('key1') is None

        # Set and get
        await cache.set('key1', 'value1')
        assert await cache.get('key1') == 'value1'

        # Set multiple
        await cache.set('key2', 'value2')
        await cache.set('key3', 'value3')

        assert await cache.get('key2') == 'value2'
        assert await cache.get('key3') == 'value3'

    async def test_cache_ttl_expiration(self) -> None:
        """Test that cache entries expire after TTL."""
        cache = TTLCache(ttl_seconds=0.1, maxsize=10)  # Very short TTL

        await cache.set('key1', 'value1')
        assert await cache.get('key1') == 'value1'

        # Wait for expiration
        await asyncio.sleep(0.15)

        assert await cache.get('key1') is None

    async def test_cache_maxsize_eviction(self) -> None:
        """Test that cache evicts oldest entries when maxsize exceeded."""
        cache = TTLCache(ttl_seconds=10.0, maxsize=2)  # Long TTL, small size

        await cache.set('key1', 'value1')
        await cache.set('key2', 'value2')

        # Both should be present
        assert await cache.get('key1') == 'value1'
        assert await cache.get('key2') == 'value2'

        # Adding third should evict oldest (key1)
        await cache.set('key3', 'value3')

        assert await cache.get('key1') is None  # Evicted
        assert await cache.get('key2') == 'value2'  # Still present
        assert await cache.get('key3') == 'value3'  # New entry

    async def test_cache_zero_ttl_disabled(self) -> None:
        """Test that zero TTL disables caching."""
        cache = TTLCache(ttl_seconds=0.0, maxsize=10)

        await cache.set('key1', 'value1')
        # With zero TTL, nothing should be cached
        assert await cache.get('key1') is None

    async def test_cache_clear(self) -> None:
        """Test cache clearing."""
        cache = TTLCache(ttl_seconds=10.0, maxsize=10)

        await cache.set('key1', 'value1')
        await cache.set('key2', 'value2')

        assert await cache.get('key1') == 'value1'
        assert await cache.get('key2') == 'value2'

        await cache.clear()

        assert await cache.get('key1') is None
        assert await cache.get('key2') is None

    async def test_cache_concurrent_access(self) -> None:
        """Test cache behavior under concurrent access."""
        cache = TTLCache(ttl_seconds=1.0, maxsize=100)

        async def set_values(prefix: str) -> None:
            for i in range(10):
                await cache.set(f'{prefix}_{i}', f'value_{prefix}_{i}')

        async def get_values(prefix: str) -> list[str | None]:
            values = []
            for i in range(10):
                values.append(await cache.get(f'{prefix}_{i}'))
            return values

        # Set values concurrently
        await asyncio.gather(
            set_values('a'),
            set_values('b'),
            set_values('c'),
        )

        # Get values concurrently
        results = await asyncio.gather(
            get_values('a'),
            get_values('b'),
            get_values('c'),
        )

        # All values should be present
        for result_set in results:
            assert len(result_set) == 10
            assert all(v is not None for v in result_set)


class TestClientCaching:
    """Test caching behavior in the client."""

    @pytest.fixture
    def fast_expiry_config(self) -> Config:
        """Config with very short cache TTL for testing."""
        return Config(
            base_url='https://example.test',
            cache_ttl=0.1,  # Very short TTL
            cache_maxsize=10,
            max_retries=0,  # No retries for faster tests
        )

    @pytest.fixture
    def no_cache_config(self) -> Config:
        """Config with caching disabled."""
        return Config(
            base_url='https://example.test',
            cache_ttl=0.0,  # Disabled
            cache_maxsize=10,
            max_retries=0,
        )

    async def test_cache_expiration_forces_new_request(
        self, mock_api, fast_expiry_config: Config
    ) -> None:
        """Test that expired cache entries trigger new API requests."""
        api, transport = mock_api
        client = FourGetClient(fast_expiry_config, transport=transport)

        api.add_json('/api/v1/web', {'status': 'ok', 'results': ['first']})

        # First request
        result1 = await client.web_search('test')
        assert result1['results'] == ['first']
        assert len(api.calls) == 1

        # Second request immediately (should use cache)
        result2 = await client.web_search('test')
        assert result2['results'] == ['first']
        assert len(api.calls) == 1  # No new request

        # Wait for cache to expire
        await asyncio.sleep(0.15)

        # Update API response
        api.add_json('/api/v1/web', {'status': 'ok', 'results': ['second']})

        # Third request after expiration (should make new request)
        result3 = await client.web_search('test')
        assert result3['results'] == ['second']
        assert len(api.calls) == 2  # New request made

    async def test_disabled_cache_always_requests(self, mock_api, no_cache_config: Config) -> None:
        """Test that disabled cache always makes new requests."""
        api, transport = mock_api
        client = FourGetClient(no_cache_config, transport=transport)

        api.add_json('/api/v1/web', {'status': 'ok', 'results': ['test']})

        # Multiple identical requests
        await client.web_search('test')
        await client.web_search('test')
        await client.web_search('test')

        # All should result in API calls
        assert len(api.calls) == 3

    async def test_cache_key_generation(self, mock_api, config: Config) -> None:
        """Test that different parameters generate different cache keys."""
        api, transport = mock_api
        client = FourGetClient(config, transport=transport)

        # Different responses for different endpoints
        api.add_json('/api/v1/web', {'status': 'ok', 'type': 'web'})
        api.add_json('/api/v1/images', {'status': 'ok', 'type': 'images'})
        api.add_json('/api/v1/news', {'status': 'ok', 'type': 'news'})

        # Different search types should not share cache
        web_result = await client.web_search('test')
        image_result = await client.image_search('test')
        news_result = await client.news_search('test')

        assert web_result['type'] == 'web'
        assert image_result['type'] == 'images'
        assert news_result['type'] == 'news'
        assert len(api.calls) == 3  # All different requests

    async def test_cache_with_different_parameters(self, mock_api, config: Config) -> None:
        """Test caching behavior with different search parameters."""
        api, transport = mock_api
        client = FourGetClient(config, transport=transport)

        def response_handler(request):
            params = dict(request.url.params)
            return {
                'status': 'ok',
                'query': params.get('s', 'unknown'),
                'extended': params.get('extendedsearch', 'false'),
            }

        api.add_responder(
            '/api/v1/web', lambda req: httpx.Response(200, json=response_handler(req))
        )

        # Different queries should have separate cache entries
        result1 = await client.web_search('query1')
        result2 = await client.web_search('query2')
        result3 = await client.web_search('query1')  # Should use cache

        assert result1['query'] == 'query1'
        assert result2['query'] == 'query2'
        assert result3['query'] == 'query1'
        assert len(api.calls) == 2  # Third was cached

    async def test_cache_eviction_under_pressure(self, mock_api, config: Config) -> None:
        """Test cache behavior when maxsize is exceeded."""
        # Create config with very small cache
        small_cache_config = Config(
            base_url=config.base_url,
            cache_ttl=60.0,  # Long TTL
            cache_maxsize=2,  # Very small cache
            max_retries=0,
        )

        api, transport = mock_api
        client = FourGetClient(small_cache_config, transport=transport)

        def unique_response(request):
            params = dict(request.url.params)
            query = params.get('s', 'unknown')
            return httpx.Response(200, json={'status': 'ok', 'query': query})

        api.add_responder('/api/v1/web', unique_response)

        # Fill cache beyond capacity
        await client.web_search('query1')  # Cache: [query1]
        await client.web_search('query2')  # Cache: [query1, query2]
        await client.web_search('query3')  # Cache: [query2, query3] (query1 evicted)

        assert len(api.calls) == 3

        # Requesting query1 again should require new API call (was evicted)
        await client.web_search('query1')  # New request
        await client.web_search('query2')  # Should be cache hit

        # query1 needed new request, query2 might also need new request due to eviction
        assert len(api.calls) >= 4  # At least query1 needed new request
        assert len(api.calls) <= 5  # query2 might also be evicted
