"""Refresh bench/snapshots/ from the servers in bench/servers.toml (needs npx and uvx).

    uv run python bench/collect.py                 # every server
    uv run python bench/collect.py server-memory   # just these

Snapshots are the exact tools/list results, so tests can replay them offline. A server that
fails is reported and skipped; its old snapshot (if any) is kept.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import tomllib

from toolism.errors import ToolismError
from toolism.formats import serialize
from toolism.loaders.mcp import load_mcp_stdio

BENCH = Path(__file__).resolve().parent
SNAPSHOTS = BENCH / "snapshots"


def servers() -> list[dict[str, str]]:
    with (BENCH / "servers.toml").open("rb") as handle:
        return list(tomllib.load(handle)["server"])


def collect(server: dict[str, str], scratch: Path, timeout: float) -> Path:
    command = server["command"].format(version=server["version"], tmp=scratch, repo=BENCH.parent)
    toolset = load_mcp_stdio(command, cwd=scratch, timeout=timeout)
    target = SNAPSHOTS / f"{server['name']}.json"
    text = json.dumps(serialize(toolset), indent=2, ensure_ascii=False) + "\n"
    target.write_text(text, encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("names", nargs="*", help="server names (default: all)")
    parser.add_argument("--timeout", type=float, default=300.0, help="seconds per server")
    args = parser.parse_args(argv)
    chosen = [s for s in servers() if not args.names or s["name"] in args.names]
    SNAPSHOTS.mkdir(exist_ok=True)
    failed = 0
    with tempfile.TemporaryDirectory(prefix="toolism-bench-") as scratch:
        for server in chosen:
            try:
                path = collect(server, Path(scratch), args.timeout)
            except ToolismError as exc:
                failed += 1
                print(f"FAIL {server['name']}: {exc.message}", file=sys.stderr)
                if exc.hint:
                    print(f"     {exc.hint}", file=sys.stderr)
                continue
            count = len(json.loads(path.read_text(encoding="utf-8"))["tools"])
            print(f"ok   {server['name']}: {count} tools -> {path.relative_to(BENCH.parent)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
