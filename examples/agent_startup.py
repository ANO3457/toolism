"""Slim tool definitions once at agent start-up, then send the slim versions on every request.

    python examples/agent_startup.py            # offline: prints the token saving
    ANTHROPIC_API_KEY=... python examples/agent_startup.py --call

toolslim.slim_tools() returns the same shape it was given (here: Anthropic tool dicts), is
cached by input, and with the default safe level never changes which tool calls validate.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import toolslim

HERE = Path(__file__).parent


def main() -> None:
    tools = json.loads((HERE / "anthropic_tools.json").read_text(encoding="utf-8"))
    slim = toolslim.slim_tools(tools)

    before = toolslim.measure(toolslim.parse(tools), tokenizer="heuristic").total
    after = toolslim.measure(toolslim.parse(slim), tokenizer="heuristic").total
    print(f"tool definitions: {before} -> {after} tokens per request (heuristic count)")

    if "--call" in sys.argv:
        import anthropic  # pip install anthropic

        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-5-5",
            max_tokens=512,
            tools=slim,
            messages=[{"role": "user", "content": "Find the docs on rotating API keys."}],
        )
        print(response.content)


if __name__ == "__main__":
    main()
