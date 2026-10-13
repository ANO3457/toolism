# C12 — MCP loader

## Responsibility

Get the exact tool definitions an MCP server advertises, by running it over stdio and calling `tools/list`.

## Interface

```python
def load_mcp_stdio(command: str | Sequence[str], *, env: Mapping[str, str] | None = None,
                   cwd: str | None = None, timeout: float = 60.0) -> ToolSet
```

## Behaviour

1. Lazy-import `mcp`. If it's missing → `MissingExtraError("pip install 'toolslim[mcp]'")`.
2. `StdioServerParameters(command=argv[0], args=argv[1:], env=env merged over os.environ, cwd=cwd)`.
3. `stdio_client` → `ClientSession` → `initialize()` → page through `list_tools(cursor)` until `nextCursor` is empty. Hard cap 100 pages.
4. Each tool → `tool.model_dump(by_alias=True, exclude_none=True, mode="json")`. This preserves `inputSchema`, `outputSchema`, `annotations`, `title` and `_meta`.
5. Return `parse({"tools": [...]})` → MCP-format ToolSet.
6. The whole exchange runs under `anyio.fail_after(timeout)`. Any failure → `LoaderError("MCP server '<cmd>' failed: …")`, with the server's stderr suppressed unless `TOOLSLIM_DEBUG`.

## Tests

- An integration test with a tiny FastMCP server (`tests/servers/demo_server.py`, run with `sys.executable`). It has two tools with Pydantic arguments; the test checks names, schemas and that slimming saves tokens.
- Marked `mcp` and skipped if the extra is missing.
- Failure path: a non-existent command → `LoaderError`.

## Review

| Issue | Change |
|---|---|
| `mcp` SDK API differences across versions (`list_tools` signature, cursor params). | Call `session.list_tools(cursor=…)` only when a cursor exists; feature-detect the parameter. Pin `mcp>=1.2`. |
| Inheriting the full environment could leak secrets to a server the user didn't intend. | The user chose to run that command themselves; same trust model as running it in a shell. Documented. |
| Servers that print to stdout break the stdio protocol. | Report a clear `LoaderError`. This is a server bug, not ours. |
