"""Entry point for running the 4get MCP server."""

from __future__ import annotations

from src.server import create_server


def main() -> None:
    server = create_server()
    server.run()


if __name__ == '__main__':
    main()
