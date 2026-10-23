"""A tiny MCP server with Pydantic-typed tools, for the loader integration test.

Run as ``python demo_server.py``. Works with the ``mcp`` SDK 1.x (FastMCP) and 2.x (MCPServer).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

try:
    from mcp.server.mcpserver import MCPServer as Server
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as Server  # type: ignore[no-redef]

server = Server("toolism-demo")


class Address(BaseModel):
    street: str = Field(description="Street and number")
    city: str = Field(description="City")
    country: str | None = Field(default=None, description="ISO country code")


@server.tool()
def create_contact(
    name: str,
    email: str | None = None,
    address: Address | None = None,
    tags: list[str] | None = None,
) -> str:
    """Create a contact in the address book.

    Use this when the user asks to save a person.
    """
    return f"created {name}"


@server.tool()
def search_contacts(
    query: str,
    limit: int = 10,
    sort: Literal["name", "created"] = "name",
) -> list[str]:
    """Search contacts by name or email."""
    return [query][:limit]


if __name__ == "__main__":
    server.run()
