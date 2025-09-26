import pytest
from fastmcp import Client

from src.server import create_server

pytestmark = pytest.mark.asyncio


async def test_web_search_tool_returns_payload(fourget_server, mock_api) -> None:
    api, _ = mock_api
    api.add_json(
        '/api/v1/web',
        {'status': 'ok', 'npt': 'token', 'web': [{'title': 'Test', 'url': 'https://example.com'}]},
    )

    async with Client(fourget_server) as client:
        result = await client.call_tool(
            'fourget_web_search',
            {'query': 'fastmcp'},
        )

    assert result.data['status'] == 'ok'
    assert len(api.calls) == 1


async def test_web_search_tool_respects_cache(fourget_server, mock_api) -> None:
    api, _ = mock_api
    api.add_json(
        '/api/v1/web',
        {'status': 'ok', 'npt': None, 'web': []},
    )

    async with Client(fourget_server) as client:
        await client.call_tool('fourget_web_search', {'query': 'fastmcp'})
        await client.call_tool('fourget_web_search', {'query': 'fastmcp'})

    assert len(api.calls) == 1


async def test_image_search_tool_targets_correct_endpoint(mock_api, config) -> None:
    api, transport = mock_api
    api.add_json(
        '/api/v1/images',
        {'status': 'ok', 'image': []},
    )

    server = create_server(config=config, transport=transport)

    async with Client(server) as client:
        result = await client.call_tool(
            'fourget_image_search',
            {'query': 'cats'},
        )

    assert result.data['status'] == 'ok'
    assert any(request.url.path == '/api/v1/images' for request in api.calls)


async def test_news_search_tool_targets_correct_endpoint(mock_api, config) -> None:
    api, transport = mock_api
    api.add_json(
        '/api/v1/news',
        {'status': 'ok', 'news': []},
    )

    server = create_server(config=config, transport=transport)

    async with Client(server) as client:
        result = await client.call_tool(
            'fourget_news_search',
            {'query': 'ai'},
        )

    assert result.data['status'] == 'ok'
    assert any(request.url.path == '/api/v1/news' for request in api.calls)
