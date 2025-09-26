import time
from unittest.mock import patch

import httpx
import pytest

from src.client import FourGetClient
from src.config import Config
from src.errors import FourGetAPIError, FourGetAuthError, FourGetError, FourGetTransportError

pytestmark = pytest.mark.asyncio


async def test_web_search_basic_caching(mock_api: tuple, fourget_client: FourGetClient) -> None:
    """Test basic caching behavior for identical requests."""
    api, _ = mock_api
    api.add_json(
        '/api/v1/web',
        {'status': 'ok', 'npt': None, 'web': [{'title': 'Result', 'url': 'https://example.com'}]},
    )

    first = await fourget_client.web_search('fastmcp')
    second = await fourget_client.web_search('fastmcp')

    assert first == second
    assert len(api.calls) == 1


async def test_web_search_uses_page_token_without_query(
    mock_api: tuple, fourget_client: FourGetClient
) -> None:
    api, _ = mock_api

    def responder(request):
        params = dict(request.url.params)
        assert 'npt' in params
        assert 's' not in params
        assert params['npt'] == 'token123'
        return httpx.Response(200, json={'status': 'ok', 'npt': 'token124'})

    api.add_responder('/api/v1/web', responder)

    payload = await fourget_client.web_search('ignored', page_token='token123')
    assert payload['status'] == 'ok'
    assert len(api.calls) == 1


async def test_extended_search_parameter_is_serialized(
    mock_api: tuple, fourget_client: FourGetClient
) -> None:
    api, _ = mock_api

    def responder(request):
        params = dict(request.url.params)
        assert params.get('extendedsearch') == 'true'
        return httpx.Response(200, json={'status': 'ok'})

    api.add_responder('/api/v1/web', responder)

    payload = await fourget_client.web_search('fastmcp', extended_search=True)
    assert payload['status'] == 'ok'


async def test_non_ok_status_raises_api_error(
    mock_api: tuple, fourget_client: FourGetClient
) -> None:
    api, _ = mock_api
    api.add_json(
        '/api/v1/web',
        {'status': 'error', 'message': 'Something went wrong'},
    )

    with pytest.raises(FourGetAPIError) as exc_info:
        await fourget_client.web_search('fastmcp')

    assert 'Something went wrong' in str(exc_info.value)


async def test_missing_status_raises_generic_error(
    mock_api: tuple, fourget_client: FourGetClient
) -> None:
    api, _ = mock_api
    api.add_json('/api/v1/web', {'results': []})

    with pytest.raises(FourGetError):
        await fourget_client.web_search('fastmcp')


async def test_429_raises_auth_error(mock_api: tuple, fourget_client: FourGetClient) -> None:
    api, _ = mock_api
    api.add_json(
        '/api/v1/web',
        {'status': 'error', 'message': 'rate limited'},
        status_code=429,
    )

    with pytest.raises(FourGetAuthError):
        await fourget_client.web_search('fastmcp')


async def test_429_retries_with_exponential_backoff(
    mock_api: tuple, fourget_client: FourGetClient
) -> None:
    api, _ = mock_api
    call_count = 0

    def rate_limit_then_success(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count <= 2:  # First two calls fail with rate limit
            return httpx.Response(429, json={'status': 'error', 'message': 'rate limited'})
        return httpx.Response(200, json={'status': 'ok', 'results': []})

    api.add_responder('/api/v1/web', rate_limit_then_success)

    start_time = time.monotonic()
    result = await fourget_client.web_search('fastmcp')
    elapsed = time.monotonic() - start_time

    assert result['status'] == 'ok'
    assert call_count == 3  # 2 failures + 1 success
    assert elapsed >= 0.1  # At least one retry delay
    assert len(api.calls) == 3


async def test_max_retries_exceeded_raises_exception(
    mock_api: tuple, fourget_client: FourGetClient
) -> None:
    api, _ = mock_api

    def always_rate_limit(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={'status': 'error', 'message': 'rate limited'})

    api.add_responder('/api/v1/web', always_rate_limit)

    with pytest.raises(FourGetAuthError, match='Rate limited'):
        await fourget_client.web_search('fastmcp')

    # Should try 4 times total (initial + 3 retries)
    assert len(api.calls) == 4


async def test_connection_error_retries(mock_api: tuple, fourget_client: FourGetClient) -> None:
    api, _ = mock_api
    call_count = 0

    def connection_error_then_success(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.ConnectError('Connection failed')
        return httpx.Response(200, json={'status': 'ok', 'results': []})

    api.add_responder('/api/v1/web', connection_error_then_success)

    result = await fourget_client.web_search('fastmcp')
    assert result['status'] == 'ok'
    assert call_count == 2  # 1 failure + 1 success


async def test_non_retryable_http_error_fails_immediately(
    mock_api: tuple, fourget_client: FourGetClient
) -> None:
    api, _ = mock_api
    api.add_json(
        '/api/v1/web',
        {'status': 'error', 'message': 'not found'},
        status_code=404,
    )

    with pytest.raises(FourGetTransportError):
        await fourget_client.web_search('fastmcp')

    # Should only try once (404 is not retryable)
    assert len(api.calls) == 1


async def test_backoff_delay_calculation() -> None:
    config = Config(
        base_url='https://example.test',
        retry_base_delay=1.0,
        retry_max_delay=10.0,
    )
    client = FourGetClient(config)

    # Test exponential backoff
    with patch('random.random', return_value=0.5):  # Fixed jitter for testing
        delay_0 = client._calculate_backoff_delay(0)
        delay_1 = client._calculate_backoff_delay(1)
        delay_2 = client._calculate_backoff_delay(2)

        # Should be approximately: base * (2^attempt) with jitter
        assert 0.75 <= delay_0 <= 1.25  # 1.0 ± 25%
        assert 1.5 <= delay_1 <= 2.5  # 2.0 ± 25%
        assert 3.0 <= delay_2 <= 5.0  # 4.0 ± 25%

    # Test max delay cap
    delay_large = client._calculate_backoff_delay(10)
    assert delay_large <= config.retry_max_delay * 1.25  # Max + jitter


async def test_config_validation() -> None:
    # Test invalid URL
    with pytest.raises(ValueError, match='Invalid base_url'):
        Config(base_url='not-a-url')._validate()

    # Test invalid scheme
    with pytest.raises(ValueError, match='base_url must use http or https scheme'):
        Config(base_url='ftp://example.com')._validate()

    # Test negative timeout
    with pytest.raises(ValueError, match='timeout must be positive'):
        Config(base_url='https://example.com', timeout=-1)._validate()

    # Test invalid retry configuration
    with pytest.raises(ValueError, match='retry_base_delay.*must not exceed.*retry_max_delay'):
        Config(
            base_url='https://example.com',
            retry_base_delay=10.0,
            retry_max_delay=5.0,
        )._validate()

    # Test invalid connection pool configuration
    with pytest.raises(
        ValueError, match='connection_pool_max_keepalive.*must not exceed.*connection_pool_maxsize'
    ):
        Config(
            base_url='https://example.com',
            connection_pool_maxsize=5,
            connection_pool_max_keepalive=10,
        )._validate()
