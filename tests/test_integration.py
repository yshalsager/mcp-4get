"""Integration tests with real 4get API.

These tests run against the actual 4get.ca API and are marked as slow.
Run with: pytest -m integration
Skip with: pytest -m "not integration"
"""

from __future__ import annotations

import asyncio
import os
import time

import pytest

from src.client import FourGetClient
from src.config import Config
from src.errors import FourGetAuthError

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


@pytest.fixture
def integration_config() -> Config:
    """Configuration for integration tests with real API."""
    return Config(
        base_url=os.environ.get('FOURGET_BASE_URL', 'https://4get.ca'),
        pass_token=os.environ.get('FOURGET_PASS'),  # Optional
        user_agent='mcp-4get-integration-test',
        timeout=30.0,  # Longer timeout for real API
        cache_ttl=10.0,  # Short TTL for cache testing
        cache_maxsize=32,
        max_retries=2,  # Fewer retries for integration tests
        retry_base_delay=1.0,
        retry_max_delay=10.0,
        connection_pool_maxsize=5,
        connection_pool_max_keepalive=2,
    )


@pytest.fixture
def integration_client(integration_config: Config) -> FourGetClient:
    """Client configured for integration testing."""
    return FourGetClient(integration_config)


@pytest.mark.slow
async def test_real_web_search(integration_client: FourGetClient) -> None:
    """Test web search against real 4get API."""
    result = await integration_client.web_search('python programming')

    assert result['status'] == 'ok'
    assert 'web' in result
    assert isinstance(result['web'], list)
    assert len(result['web']) > 0

    # Check structure of first result
    first_result = result['web'][0]
    assert 'title' in first_result
    assert 'url' in first_result
    assert isinstance(first_result['title'], str)
    assert isinstance(first_result['url'], str)


@pytest.mark.slow
async def test_real_image_search(integration_client: FourGetClient) -> None:
    """Test image search against real 4get API."""
    result = await integration_client.image_search('cats')

    assert result['status'] == 'ok'
    assert 'image' in result
    assert isinstance(result['image'], list)

    if result['image']:  # May be empty
        first_image = result['image'][0]
        assert 'url' in first_image
        assert isinstance(first_image['url'], str)


@pytest.mark.slow
async def test_real_news_search(integration_client: FourGetClient) -> None:
    """Test news search against real 4get API."""
    result = await integration_client.news_search('technology')

    assert result['status'] == 'ok'
    assert 'news' in result
    assert isinstance(result['news'], list)

    if result['news']:  # May be empty
        first_news = result['news'][0]
        assert 'title' in first_news
        assert 'url' in first_news


@pytest.mark.slow
async def test_pagination_with_real_api(integration_client: FourGetClient) -> None:
    """Test pagination using real API page tokens."""
    # Get first page
    first_page = await integration_client.web_search('programming languages')
    assert first_page['status'] == 'ok'

    # Check if pagination token exists
    page_token = first_page.get('npt')
    if page_token:
        # Get second page using token
        second_page = await integration_client.web_search(
            'ignored query',  # Should be ignored when using page_token
            page_token=page_token,
        )
        assert second_page['status'] == 'ok'
        assert 'web' in second_page

        # Results should be different (not foolproof but likely)
        if (
            first_page.get('web')
            and second_page.get('web')
            and len(first_page['web']) > 0
            and len(second_page['web']) > 0
        ):
            assert first_page['web'][0] != second_page['web'][0]


@pytest.mark.slow
async def test_rate_limiting_with_concurrent_requests(
    integration_client: FourGetClient,
) -> None:
    """Test rate limiting behavior with concurrent requests."""
    queries = [
        'python',
        'javascript',
        'rust',
        'go',
        'java',
        'typescript',
        'kotlin',
        'swift',
        'c++',
        'ruby',
    ]

    # Make many concurrent requests to potentially trigger rate limiting
    tasks = [integration_client.web_search(query) for query in queries]

    start_time = time.monotonic()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = time.monotonic() - start_time

    # Count successful vs failed requests
    successful = sum(1 for r in results if isinstance(r, dict) and r.get('status') == 'ok')
    rate_limited = sum(1 for r in results if isinstance(r, FourGetAuthError))

    # At least some requests should succeed
    assert successful > 0

    # If rate limited, should have taken time (due to retries)
    if rate_limited > 0:
        assert elapsed > 1.0  # Should have some retry delays

    print(
        f'Requests: {len(queries)}, Successful: {successful}, Rate limited: {rate_limited}, Time: {elapsed:.2f}s'
    )


@pytest.mark.slow
async def test_extended_search_parameter(integration_client: FourGetClient) -> None:
    """Test extended search parameter with real API."""
    # Test with extended search enabled
    result_extended = await integration_client.web_search('machine learning', extended_search=True)
    assert result_extended['status'] == 'ok'

    # Test with extended search disabled
    result_normal = await integration_client.web_search('machine learning', extended_search=False)
    assert result_normal['status'] == 'ok'

    # Both should return results (content may differ)
    assert 'web' in result_extended
    assert 'web' in result_normal


@pytest.mark.slow
async def test_invalid_search_query_handling(integration_client: FourGetClient) -> None:
    """Test how real API handles invalid or empty queries."""
    # Test empty query
    try:
        result = await integration_client.web_search('')
        # API might accept empty query or return error
        if result['status'] == 'ok':
            assert 'web' in result
    except Exception:
        # API might reject empty queries - this is acceptable
        pass

    # Test very long query
    long_query = 'a' * 1000
    try:
        result = await integration_client.web_search(long_query)
        if result['status'] == 'ok':
            assert 'web' in result
    except Exception:
        # API might reject very long queries - this is acceptable
        pass


@pytest.mark.slow
async def test_api_response_time_reasonable(integration_client: FourGetClient) -> None:
    """Test that API responses come back in reasonable time."""
    start_time = time.monotonic()
    result = await integration_client.web_search('fast query test')
    elapsed = time.monotonic() - start_time

    assert result['status'] == 'ok'
    assert elapsed < 15.0  # Should respond within 15 seconds

    print(f'API response time: {elapsed:.2f}s')


@pytest.mark.slow
async def test_connection_resilience(integration_config: Config) -> None:
    """Test connection handling with very limited pool size."""
    # Create client with minimal connection pool
    limited_config = Config(
        base_url=integration_config.base_url,
        pass_token=integration_config.pass_token,
        user_agent=integration_config.user_agent,
        timeout=30.0,
        cache_ttl=0.0,  # Disable caching to force real requests
        cache_maxsize=1,
        max_retries=1,
        retry_base_delay=0.5,
        retry_max_delay=2.0,
        connection_pool_maxsize=1,  # Very limited
        connection_pool_max_keepalive=1,
    )

    client = FourGetClient(limited_config)

    # Make sequential requests to test connection reuse
    queries = ['test1', 'test2', 'test3']
    for query in queries:
        result = await client.web_search(query)
        assert result['status'] == 'ok'


if __name__ == '__main__':
    # Allow running integration tests directly
    pytest.main([__file__, '-v', '-s'])
