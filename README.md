# 4get MCP Server

A [MCP server](https://modelcontextprotocol.io/introduction) that provides seamless access to the [4get Meta Search engine](https://4get.ca) API for LLM clients via [FastMCP](https://gofastmcp.com/).

[![Codacy Badge](https://app.codacy.com/project/badge/Grade/2c9f817e8b934159bccbb6581ccaf4bf)](https://app.codacy.com/gh/yshalsager/mcp-4get/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade) [![Codacy Badge](https://app.codacy.com/project/badge/Coverage/2c9f817e8b934159bccbb6581ccaf4bf)](https://app.codacy.com/gh/yshalsager/mcp-4get/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_coverage)
[![PyPI version](https://badge.fury.io/py/mcp-4get.svg)](https://pypi.org/project/mcp-4get/)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/mcp-4get?period=total\&units=international_system\&left_color=grey\&right_color=blue\&left_text=Total%20Downloads%20\(PyPI\))](https://pepy.tech/project/mcp-4get)

[![GitHub release](https://img.shields.io/github/release/yshalsager/mcp-4get.svg)](https://github.com/yshalsager/mcp-4get/releases/)
[![GitHub Downloads](https://img.shields.io/github/downloads/yshalsager/mcp-4get/total.svg)](https://github.com/yshalsager/mcp-4get/releases/latest)

[![made-with-python](https://img.shields.io/badge/Made%20with-Python%203-3776AB?style=flat\&labelColor=3776AB\&logo=python\&logoColor=white\&link=https://www.python.org/)](https://www.python.org/)
[![Open Source Love](https://badges.frapsoft.com/os/v1/open-source.svg?v=103)](https://github.com/ellerbrock/open-source-badges/)

[![PayPal](https://img.shields.io/badge/PayPal-Donate-00457C?style=flat\&labelColor=00457C\&logo=PayPal\&logoColor=white\&link=https://www.paypal.me/yshalsager)](https://www.paypal.me/yshalsager)
[![LiberaPay](https://img.shields.io/badge/Liberapay-Support-F6C915?style=flat\&labelColor=F6C915\&logo=Liberapay\&logoColor=white\&link=https://liberapay.com/yshalsager)](https://liberapay.com/yshalsager)

## ✨ Features

- **🔍 Multi Search Functions**: Web, image, and news search with comprehensive result formatting
- **⚡ Smart Caching**: TTL-based response caching with configurable size limits
- **🔄 Retry Logic**: Exponential backoff for rate-limited and network errors
- **🏗️ Production Ready**: Connection pooling, comprehensive error handling, and validation
- **📊 Rich Responses**: Featured answers, related searches, pagination support, and more
- **🧪 Well Tested**: Extensive test suite including integration tests with real API, unit tests, and more
- **⚙️ Highly Configurable**: 11+ environment variables for fine-tuning
- **🎯 Engine Shorthands**: Pick a 4get scraper via the `engine` parameter without memorizing query strings

## 📋 Requirements

- **Python 3.13+**
- **[uv](https://github.com/astral-sh/uv)** for dependency management

### Quick Start

```bash
# Install dependencies
uv sync

# Run the server
uv run -m mcp_4get

# Or use mise
mise run
```

## ⚙️ Configuration

The server is highly configurable via environment variables. All settings have sensible defaults for the public `https://4get.ca` instance.

### Core Settings
| Variable | Description | Default |
| --- | --- | --- |
| `FOURGET_BASE_URL` | Base URL for the 4get instance | `https://4get.ca` |
| `FOURGET_PASS` | Optional pass token for rate-limited instances | unset |
| `FOURGET_USER_AGENT` | Override User-Agent header | `mcp-4get/<version>` |
| `FOURGET_TIMEOUT` | Request timeout in seconds | `20.0` |

### Caching & Performance
| Variable | Description | Default |
| --- | --- | --- |
| `FOURGET_CACHE_TTL` | Cache lifetime in seconds | `600.0` |
| `FOURGET_CACHE_MAXSIZE` | Maximum cached responses | `128` |
| `FOURGET_CONNECTION_POOL_MAXSIZE` | Max concurrent connections | `10` |
| `FOURGET_CONNECTION_POOL_MAX_KEEPALIVE` | Max persistent connections | `5` |

### Retry & Resilience
| Variable | Description | Default |
| --- | --- | --- |
| `FOURGET_MAX_RETRIES` | Maximum retry attempts | `3` |
| `FOURGET_RETRY_BASE_DELAY` | Base retry delay in seconds | `1.0` |
| `FOURGET_RETRY_MAX_DELAY` | Maximum retry delay in seconds | `60.0` |

## 🚀 Running the Server

### Local Development
```bash
uv run -m mcp_4get
```

### Production Deployment
```bash
# With custom configuration
export FOURGET_BASE_URL="https://my-4get-instance.com"
export FOURGET_PASS="my-secret-token"
export FOURGET_CACHE_TTL="300"
export FOURGET_MAX_RETRIES="5"

uv run -m mcp_4get
```

### MCP Server Integration

You can integrate the 4get MCP server with popular IDEs and AI assistants. Here are configuration examples:

#### Cursor IDE

Add this to your Cursor MCP configuration (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "4get": {
      "command": "uvx",
      "args": [
        "mcp_4get@latest"
      ],
      "env": {
        "FOURGET_BASE_URL": "https://4get.ca"
      }
    }
  }
}
```

#### OpenAI Codex

Add this to your Codex MCP configuration (`~/.codex/config.toml`):

```toml
[mcp_servers.4get]
command = "uvx"
args = ["mcp_4get@latest"]
env = { FOURGET_BASE_URL = "https://4get.ca" }
```

**Note**: Replace `/path/to/your/mcp-4get` with the actual path to your project directory.

## 🔧 MCP Tools

The server exposes three powerful search tools with comprehensive response formatting:

### `fourget_web_search`
```python
fourget_web_search(
    query: str,
    page_token: str = None,        # Use 'npt' from previous response
    extended_search: bool = False, # Enable extended search mode
    engine: str = None,             # Pick a scraper from the supported engine list
    extra_params: dict = None      # Language, region, etc.
)
```

**Response includes**: `web[]`, `answer[]`, `spelling`, `related[]`, `npt`

### `fourget_image_search`
```python
fourget_image_search(
    query: str,
    page_token: str = None,   # Use 'npt' from previous response
    engine: str = None,       # Pick a scraper from the supported engine list
    extra_params: dict = None # Size, color, type filters
)
```

**Response includes**: `image[]`, `npt`

### `fourget_news_search`
```python
fourget_news_search(
    query: str,
    page_token: str = None,   # Use 'npt' from previous response
    engine: str = None,       # Pick a scraper from the supported engine list
    extra_params: dict = None # Date range, source filters
)
```

**Response includes**: `news[]`, `npt`

#### Engine shorthands

All MCP tools accept an optional `engine` argument that maps directly to the 4get `scraper` query parameter. This shorthand overrides any `scraper` value you may include in `extra_params`.

| Value | Engine |
| ----- | ------ |
| `ddg` | DuckDuckGo |
| `brave` | Brave |
| `mullvad_brave` | Mullvad (Brave) |
| `yandex` | Yandex |
| `google` | Google |
| `google_cse` | Google CSE |
| `mullvad_google` | Mullvad (Google) |
| `startpage` | Startpage |
| `qwant` | Qwant |
| `ghostery` | Ghostery |
| `yep` | Yep |
| `greppr` | Greppr |
| `crowdview` | Crowdview |
| `mwmbl` | Mwmbl |
| `mojeek` | Mojeek |
| `baidu` | Baidu |
| `coccoc` | Coc Coc |
| `solofield` | Solofield |
| `marginalia` | Marginalia |
| `wiby` | wiby |
| `curlie` | Curlie |

If you need to pass additional 4get query parameters (such as `country` or `language`), continue to supply them through `extra_params`.

### 📄 Pagination
All tools support pagination via the `npt` (next page token):

```python
# Get first page
result = await client.web_search("python programming")

# Get next page if available
if result.get('npt'):
    next_page = await client.web_search("ignored", page_token=result['npt'])
```

## 🐍 Using the Async Client Directly

You can reuse the bundled async client outside MCP for direct API access:

```python
import asyncio
from mcp_4get.client import FourGetClient
from mcp_4get.config import Config

async def main() -> None:
    client = FourGetClient(Config.from_env())
    data = await client.web_search(
        "model context protocol",
        options={"scraper": "mullvad_brave"},
    )
    for result in data.get("web", []):
        print(result["title"], "->", result["url"])

asyncio.run(main())
```

This allows you to integrate 4get search capabilities directly into your Python applications without going through the MCP protocol.

## 🛡️ Error Handling & Resilience

### Automatic Retry Logic
- **Rate Limiting (429)**: Exponential backoff with jitter
- **Network Errors**: Connection failures and timeouts
- **Non-retryable**: HTTP 404/500 errors fail immediately

### Error Types
- `FourGetAuthError`: Rate limited or invalid authentication
- `FourGetAPIError`: API returned non-success status
- `FourGetTransportError`: Network or HTTP protocol errors
- `FourGetError`: Generic client errors

### Configuration Validation
All settings are validated on startup with clear error messages for misconfigurations.

## 📊 Response Format

Based on the real 4get API, responses include rich metadata:

```json
{
  "status": "ok",
  "web": [
    {
      "title": "Example Result",
      "description": "Result description...",
      "url": "https://example.com",
      "date": 1640995200,
      "type": "web"
    }
  ],
  "answer": [
    {
      "title": "Featured Answer",
      "description": [{"type": "text", "value": "Answer content..."}],
      "url": "https://source.com",
      "table": {"Key": "Value"}
    }
  ],
  "spelling": {
    "type": "no_correction",
    "correction": null
  },
  "related": ["related search", "terms"],
  "npt": "pagination_token_here"
}
```

## Development

This project uses several tools to streamline the development process:

### mise

[mise](https://mise.jdx.dev/) is used for managing project-level dependencies and environment variables. mise helps
ensure consistent development environments across different machines.

To get started with mise:

1. Install mise by following the instructions on the [official website](https://mise.jdx.dev/).
2. Run `mise install` in the project root to set up the development environment.

**Environment Variable Overrides**: You can override any environment variable by creating a `.mise.local.toml` file in the project root:

```toml
[env]
FOURGET_BASE_URL = "https://your-custom-4get-instance.com"
FOURGET_CACHE_TTL = "300"
# Add any other environment variables you want to override
```

This file is automatically loaded by mise and allows you to customize your local development environment without modifying the shared configuration files.

### UV

[UV](https://docs.astral.sh/uv/) is used for dependency management and packaging. It provides a clean,
version-controlled way to manage project dependencies.

To set up the project with UV:

1. Install UV using mise, or by following the instructions on the [official website](https://docs.astral.sh/uv/getting-started/installation/).
2. Run `uv sync` to install project dependencies.

### MCP Server Integration for local development

#### Cursor IDE

Add this to your Cursor MCP configuration (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "4get": {
      "command": "uv",
      "args": [
        "run",
        "--project",
        "/path/to/your/mcp-4get",
        "-m",
        "src"
      ],
      "env": {
        "FOURGET_BASE_URL": "https://4get.ca"
      }
    }
  }
}
```

#### OpenAI Codex

Add this to your Codex MCP configuration (`~/.codex/config.toml`):

```toml
[mcp_servers.4get]
command = "uv"
args = ["run", "--project", "/path/to/your/mcp-4get", "-m", "src"]
env = { FOURGET_BASE_URL = "https://4get.ca" }
```

**Note**: Replace `/path/to/your/mcp-4get` with the actual path to your project directory.

## 🧪 Testing

Comprehensive test suite with unit, integration, and performance tests:

```bash
# Run all tests
uv run pytest

# Run only fast unit tests (exclude integration)
uv run pytest -m "not integration"

# Run integration tests with real 4get API
uv run pytest -m integration

# Run with coverage
uv run pytest --cov=src

# Run specific test categories
uv run pytest tests/test_cache.py      # Cache behavior tests
uv run pytest tests/test_client.py     # Client and retry logic tests
uv run pytest tests/test_integration.py # Real API integration tests
```

### Test Categories

- **Unit Tests**: Fast, deterministic tests using mock transports
- **Integration Tests**: Real API tests with rate limiting and resilience validation
- **Cache Tests**: TTL expiration, eviction policies, concurrent access
- **Retry Tests**: Exponential backoff, error handling, timeout scenarios
- **Configuration Tests**: Validation logic and environment variable parsing

The tests follow [FastMCP testing guidelines](https://gofastmcp.com/development/tests) with comprehensive fixtures and proper isolation.

## 🤝 Contributing

1. **Setup**: See [Development](#development) and [Quick Start](#quick-start) sections
2. **Tests**: See [Testing](#testing) section
3. **Linting**: `uv run ruff check`
4. **Format**: `uv run ruff format`

## 📄 License

GPLv3 License - see LICENSE file for details.
