# Component designs

Each document has the same parts:
- **Responsibility**
- **Interface**
- **Behaviour & edge cases**
- **Tests**
- **Review** — problems found in the design, and how it changed before any code was written

| # | Component | Doc |
|---|---|---|
| C0 | Scaffold & tooling | [C00-scaffold.md](C00-scaffold.md) |
| C1 | Models & errors | [C01-models.md](C01-models.md) |
| C2 | Formats & IO | [C02-formats-io.md](C02-formats-io.md) |
| C3 | Schema utilities | [C03-schema-utils.md](C03-schema-utils.md) |
| C4 | Tokenizers | [C04-tokenizers.md](C04-tokenizers.md) |
| C5 | Rule engine | [C05-rule-engine.md](C05-rule-engine.md) |
| C6 | Rule catalogue | [C06-rules.md](C06-rules.md) |
| C7 | Pipeline | [C07-pipeline.md](C07-pipeline.md) |
| C8 | Equivalence verification | [C08-verify.md](C08-verify.md) |
| C9 | Measure & reports | [C09-measure-report.md](C09-measure-report.md) |
| C10 | Baseline check | [C10-check.md](C10-check.md) |
| C11 | CLI | [C11-cli.md](C11-cli.md) |
| C12 | MCP loader | [C12-mcp-loader.md](C12-mcp-loader.md) |
| C13 | GitHub Action, CI & release | [C13-action-ci.md](C13-action-ci.md) |
| C14 | Benchmark | [C14-benchmark.md](C14-benchmark.md) |
| C15 | Documentation | [C15-docs.md](C15-docs.md) |

**Planned build order:** C0 → C1 → C2 → C3 → C4 → C5 → C6 → C7 → C8 → C9 → C10 → C11 → C12 → C13 → C14 → C15.

**Actual:** C0 → C1 → C2 → C3 → C4 → C5 → C8 → C6 → C7 → C9 → C10 → C12 → C11 → C13 → C14 → C15. Deviations from these designs are listed in [ARCHITECTURE.md §15](../architecture/ARCHITECTURE.md#15-implementation-notes).

Each component is built, tested, self-reviewed, fixed and committed before the next one starts.
