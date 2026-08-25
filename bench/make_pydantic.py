"""Generate bench/snapshots/fastmcp-pydantic.json: a typical Python MCP server.

The tools are ordinary Pydantic-typed functions with docstrings, served by the installed MCP
Python SDK (FastMCP in 1.x, MCPServer in 2.x), so the schemas are exactly what the SDK emits.

    uv run python bench/make_pydantic.py           # write the snapshot
    uv run python bench/make_pydantic.py --serve   # run as a stdio MCP server
"""

from __future__ import annotations

import json
import sys
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

try:
    from mcp.server.mcpserver import MCPServer as Server
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as Server  # type: ignore[no-redef]

server = Server("crm")


class Priority(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"


class Address(BaseModel):
    street: str = Field(description="Street and house number")
    city: str = Field(description="City")
    postal_code: str | None = Field(default=None, description="Postal code")
    country: str = Field(default="US", description="ISO 3166 country code")


class Contact(BaseModel):
    name: str = Field(description="Full name")
    email: str | None = Field(default=None, description="Email address")
    phone: str | None = None
    company_id: str | None = Field(default=None, description="The company ID")
    address: Address | None = None
    tags: list[str] = Field(default_factory=list, description="Free-form tags")


class DealUpdate(BaseModel):
    stage: Literal["lead", "qualified", "proposal", "won", "lost"] | None = None
    amount: float | None = Field(default=None, description="Deal value in USD")
    close_date: date | None = Field(default=None, description="Expected close date")
    owner_id: str | None = Field(default=None, description="Owner ID")


@server.tool()
def create_contact(contact: Contact) -> str:
    """Create a contact.

    Use this when the user asks to add a person to the CRM. Check for an existing
    contact with search_contacts first, to avoid duplicates.
    """
    return contact.name


@server.tool()
def search_contacts(
    query: str,
    company_id: str | None = None,
    tags: list[str] | None = None,
    limit: int = Field(default=20, ge=1, le=100, description="Maximum results"),
    cursor: str | None = None,
) -> list[str]:
    """Search contacts by name, email or phone.

    Results are sorted by relevance. Pass the returned cursor to get the next page.
    """
    return [query]


@server.tool()
def update_deal(deal_id: str, update: DealUpdate, notify_owner: bool = False) -> str:
    """Update a deal's stage, amount, close date or owner."""
    return deal_id


@server.tool()
def log_activity(
    contact_id: str,
    kind: Literal["call", "email", "meeting", "note"],
    summary: str = Field(description="What happened, in one or two sentences"),
    occurred_on: date | None = None,
    priority: Priority = Priority.normal,
) -> str:
    """Log an activity against a contact.

    Activities appear on the contact's timeline.
    """
    return contact_id


@server.tool()
def list_pipelines(include_archived: bool = False) -> list[str]:
    """List sales pipelines."""
    return []


@server.tool()
def merge_contacts(primary_id: str, duplicate_ids: list[str], dry_run: bool = True) -> str:
    """Merge duplicate contacts into a primary contact.

    All activities, deals and tags move to the primary contact. Use dry_run to preview.
    """
    return primary_id


def write_snapshot() -> Path:
    from toolslim.formats import serialize
    from toolslim.loaders.mcp import load_mcp_stdio

    toolset = load_mcp_stdio([sys.executable, __file__, "--serve"], timeout=120)
    target = Path(__file__).resolve().parent / "snapshots" / "fastmcp-pydantic.json"
    text = json.dumps(serialize(toolset), indent=2, ensure_ascii=False) + "\n"
    target.write_text(text, encoding="utf-8")
    return target


if __name__ == "__main__":
    if "--serve" in sys.argv:
        server.run()
    else:
        print(f"wrote {write_snapshot()}")
