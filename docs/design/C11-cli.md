# C11 — CLI

## Responsibility

A thin, predictable command-line layer over the library. No business logic lives here.

## Commands

```
toolism measure [SOURCE] [--mcp CMD] [-t/--tokenizer T] [-f/--format table|json|markdown] [-o FILE]
toolism slim    [SOURCE] [--mcp CMD] [-o FILE] [--level safe|annotations] [-e/--enable R]... [-d/--disable R]...
                 [--option R.key=value]... [--verify] [--verify-examples N] [--fail-on-rollback]
                 [-t T] [-r/--report table|json|markdown] [--report-file FILE] [--compact]
toolism check   [SOURCE] [--mcp CMD] -b/--baseline FILE [--max-increase X] [--max-total N] [--max-tool N]
                 [--update-baseline] [--allow-tokenizer-change] [-t T] [-f table|markdown|json] [--summary-md FILE]
toolism rules   [-f table|json]
toolism --version
```

## Behaviour

**Input.** `SOURCE` is a path or `-` (stdin). Exactly one of `SOURCE` / `--mcp` is required (usage error otherwise).

**Streams:**
- `slim` writes the slimmed JSON to `-o` or stdout, and the report to stderr (or `--report-file`). So `toolism slim tools.json > slim.json` gives clean JSON.
- `measure`, `check` and `rules` write their report to stdout (or `-o`).

**Exit codes:**
- `0` OK
- `1` check failed / rollback with `--fail-on-rollback`
- `2` usage, format, rule, baseline or loader error
- `3` tokenizer unavailable
- Errors print a single line `error: …` (plus a `hint: …` line when there is one) to stderr. No tracebacks unless `TOOLISM_DEBUG=1`.

**GitHub.** When `GITHUB_STEP_SUMMARY` is set, `check` appends its markdown report to that file. `--summary-md FILE` writes it to an explicit file.

**`check --update-baseline`** writes the baseline from the current measurement and exits 0.

**Rich output** goes to the real terminal width. When stdout isn't a TTY, plain output with no colour.

## Tests

`typer.testing.CliRunner` for every command:
- happy paths
- each exit code
- stdin input
- stdout/stderr separation for `slim`
- step summary file written
- `--option` parsing errors
- `--mcp` without the extra → exit 2 with the pip hint

## Review

| Issue | Change |
|---|---|
| Mixing report and data on stdout for `slim` breaks pipes. | Report goes to stderr by design. |
| Typer's default rich tracebacks leak internals for user errors. | `pretty_exceptions_enable=False`; one central error handler maps exceptions to exit codes. |
| `--mcp` takes a shell-like string. Splitting it on Windows differs. | Use `shlex.split(posix=(os.name != "nt"))`. Document quoting. |
