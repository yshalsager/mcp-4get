from dataclasses import dataclass, field
from typing import Any, Callable

import httpx
import pytest

from src.client import FourGetClient
from src.config import Config
from src.server import create_server

Responder = Callable[[httpx.Request], httpx.Response]


@dataclass
class MockAPI:
    responses: dict[str, Responder] = field(default_factory=dict)
    calls: list[httpx.Request] = field(default_factory=list)

    def add_json(self, path: str, payload: dict[str, Any], status_code: int = 200) -> None:
        def responder(_: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=status_code, json=payload)

        self.responses[path] = responder

    def add_responder(self, path: str, responder: Responder) -> None:
        self.responses[path] = responder

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        responder = self.responses.get(request.url.path)
        if responder is None:
            raise AssertionError(f'Unexpected request to {request.url.path}')
        return responder(request)


@pytest.fixture
def config() -> Config:
    return Config(
        base_url='https://example.test',
        pass_token=None,
        user_agent='pytest-agent',
        timeout=5.0,
        cache_ttl=600.0,
        cache_maxsize=32,
        max_retries=3,
        retry_base_delay=0.1,  # Fast for tests
        retry_max_delay=1.0,  # Fast for tests
        connection_pool_maxsize=10,
        connection_pool_max_keepalive=5,
    )


@pytest.fixture
def mock_api() -> tuple[MockAPI, httpx.MockTransport]:
    api = MockAPI()
    transport = httpx.MockTransport(api.handler)
    return api, transport


@pytest.fixture
def fourget_client(config: Config, mock_api: tuple[MockAPI, httpx.MockTransport]) -> FourGetClient:
    _, transport = mock_api
    return FourGetClient(config, transport=transport)


@pytest.fixture
def fourget_server(config: Config, mock_api: tuple[MockAPI, httpx.MockTransport]):
    _, transport = mock_api
    server = create_server(config=config, transport=transport)
    return server
