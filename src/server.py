"""FastMCP server definition for the 4get meta search API."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Awaitable, Callable

import httpx
from fastmcp import FastMCP
from pydantic import Field

from src.cache import TTLCache
from src.client import FourGetClient
from src.config import Config


class SearchEngine(str, Enum):
    """Enumeration of supported 4get scrapers with human-friendly labels."""

    DUCKDUCKGO = ('ddg', 'DuckDuckGo')
    BRAVE = ('brave', 'Brave')
    MULLVAD_BRAVE = ('mullvad_brave', 'Mullvad (Brave)')
    YANDEX = ('yandex', 'Yandex')
    GOOGLE = ('google', 'Google')
    GOOGLE_CSE = ('google_cse', 'Google CSE')
    MULLVAD_GOOGLE = ('mullvad_google', 'Mullvad (Google)')
    STARTPAGE = ('startpage', 'Startpage')
    QWANT = ('qwant', 'Qwant')
    GHOSTERY = ('ghostery', 'Ghostery')
    YEP = ('yep', 'Yep')
    GREPPR = ('greppr', 'Greppr')
    CROWDVIEW = ('crowdview', 'Crowdview')
    MWMBL = ('mwmbl', 'Mwmbl')
    MOJEEK = ('mojeek', 'Mojeek')
    BAIDU = ('baidu', 'Baidu')
    COCCOC = ('coccoc', 'Coc Coc')
    SOLOFIELD = ('solofield', 'Solofield')
    MARGINALIA = ('marginalia', 'Marginalia')
    WIBY = ('wiby', 'wiby')
    CURLIE = ('curlie', 'Curlie')

    def __new__(cls, value: str, label: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.display_name = label
        return obj

    def __str__(self) -> str:  # pragma: no cover - exercised via enumNames metadata
        return self.display_name


EngineParam = Annotated[
    SearchEngine | None,
    Field(description='Optional search engine override (maps to 4get "scraper" query parameter).'),
]


def create_server(
    config: Config | None = None,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> FastMCP:
    """Create and configure the FastMCP server for 4get API integration.

    This function sets up the MCP server with three search tools (web, image, news)
    that connect to the 4get meta search engine API.

    Args:
        config: Configuration instance. If None, will be created from environment.
        transport: Custom HTTP transport for testing. Uses default if None.

    Returns:
        Configured FastMCP server instance ready to serve MCP clients.

    Example:
        >>> # Basic usage
        >>> server = create_server()
        >>> server.run()
        >>>
        >>> # Custom configuration
        >>> config = Config(
        >>>     base_url="https://my-4get-instance.com",
        >>>     cache_ttl=300.0
        >>> )
        >>> server = create_server(config)
        >>> server.run()
    """

    config = config or Config.from_env()
    cache = TTLCache(config.cache_ttl, config.cache_maxsize)
    client = FourGetClient(config, cache=cache, transport=transport)

    mcp = FastMCP(name='fourget')

    def register_tool(
        *,
        name: str,
        description: str,
    ) -> Callable[
        [Callable[..., Awaitable[dict[str, Any]]]], Callable[..., Awaitable[dict[str, Any]]]
    ]:
        def decorator(
            func: Callable[..., Awaitable[dict[str, Any]]],
        ) -> Callable[..., Awaitable[dict[str, Any]]]:
            return mcp.tool(
                name=name,
                description=description,
                annotations={'readOnlyHint': True, 'idempotentHint': True},
            )(func)

        return decorator

    def combine_options(
        engine: SearchEngine | None, extras: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if engine is None and not extras:
            return None

        options = dict(extras) if extras else {}
        if engine is not None:
            options['scraper'] = engine.value
        return options

    @register_tool(
        name='fourget_web_search',
        description=(
            'Search the web using the 4get meta search engine. Returns web results '
            'with titles, URLs, descriptions, and optional featured answers. '
            "Supports pagination via the 'npt' token and extended search mode."
        ),
    )
    async def fourget_web_search(
        query: str,
        page_token: str | None = None,
        extended_search: bool = False,
        engine: EngineParam = None,
        extra_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await client.web_search(
            query=query,
            page_token=page_token,
            extended_search=extended_search,
            options=combine_options(engine, extra_params),
        )

    @register_tool(
        name='fourget_image_search',
        description=(
            'Search for images using the 4get meta search engine. Returns image '
            'results with URLs, thumbnails, and metadata. Supports pagination '
            "via the 'npt' token and various image filters."
        ),
    )
    async def fourget_image_search(
        query: str,
        page_token: str | None = None,
        engine: EngineParam = None,
        extra_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await client.image_search(
            query=query,
            page_token=page_token,
            options=combine_options(engine, extra_params),
        )

    @register_tool(
        name='fourget_news_search',
        description=(
            'Search for news articles using the 4get meta search engine. Returns '
            'recent news with titles, URLs, descriptions, publication dates, and '
            "thumbnails. Supports pagination via the 'npt' token."
        ),
    )
    async def fourget_news_search(
        query: str,
        page_token: str | None = None,
        engine: EngineParam = None,
        extra_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await client.news_search(
            query=query,
            page_token=page_token,
            options=combine_options(engine, extra_params),
        )

    return mcp
