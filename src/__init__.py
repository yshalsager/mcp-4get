"""4get MCP server package."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:  # pragma: no cover - fallback only triggers when metadata missing
    __version__: str = version('mcp-4get')
except PackageNotFoundError:  # pragma: no cover
    __version__ = '0.1.0'

from .server import create_server  # noqa: E402

__all__ = ['create_server', '__version__']
