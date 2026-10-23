"""The benchmark corpus as a correctness suite (design C14, review R15).

Every snapshot in bench/snapshots/ is a real tools/list result. For each one: exact round-trip,
inputs never mutated, idempotence, and (slow) bidirectional validation equivalence of every
schema the default rules change.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from toolism.formats import parse, serialize
from toolism.pipeline import slim
from toolism.verify import Verdict, check_equivalence, verify_available

BENCH = Path(__file__).resolve().parents[1] / "bench"
SNAPSHOTS = sorted((BENCH / "snapshots").glob("*.json"))
LEVELS = ["safe", "annotations"]


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def test_corpus_is_present() -> None:
    assert len(SNAPSHOTS) >= 10


@pytest.mark.parametrize("path", SNAPSHOTS, ids=lambda p: p.stem)
def test_round_trip_is_exact(path: Path) -> None:
    document = load(path)
    assert serialize(parse(document)) == document


@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize("path", SNAPSHOTS, ids=lambda p: p.stem)
def test_slim_is_idempotent_and_pure(path: Path, level: str) -> None:
    document = load(path)
    pristine = copy.deepcopy(document)
    toolset = parse(document)
    once = slim(toolset, level=level, tokenizer="heuristic")
    assert document == pristine  # the input document is never mutated
    assert serialize(toolset) == pristine
    twice = slim(once.toolset, level=level, tokenizer="heuristic")
    assert serialize(twice.toolset) == serialize(once.toolset)
    assert twice.report.saved == 0
    assert once.report.after <= once.report.before


@pytest.mark.slow
@pytest.mark.skipif(not verify_available(), reason="verify extra not installed")
@pytest.mark.parametrize("path", SNAPSHOTS, ids=lambda p: p.stem)
def test_default_rules_are_validation_equivalent(path: Path) -> None:
    toolset = parse(load(path))
    slimmed = slim(toolset, tokenizer="heuristic").toolset
    counterexamples, skipped = [], []
    for before, after in zip(toolset.tools, slimmed.tools, strict=True):
        if before.opaque or before.input_schema == after.input_schema:
            continue
        result = check_equivalence(
            before.input_schema, after.input_schema, tool=before.name, max_examples=40
        )
        if result.verdict is Verdict.COUNTEREXAMPLE:
            counterexamples.append((before.name, result.direction, result.example))
        elif result.verdict is Verdict.SKIPPED:
            skipped.append((before.name, result.reason))
    if skipped:
        print(f"{path.stem}: skipped {skipped}")
    assert counterexamples == []


def test_results_cover_every_snapshot() -> None:
    results = load(BENCH / "results.json")
    assert sorted(r["name"] for r in results["snapshots"]) == [p.stem for p in SNAPSHOTS]
    assert "| **All** |" in (BENCH / "RESULTS.md").read_text(encoding="utf-8")


def test_every_listed_server_has_a_snapshot() -> None:
    tomllib = pytest.importorskip("tomllib")
    with (BENCH / "servers.toml").open("rb") as handle:
        names = {server["name"] for server in tomllib.load(handle)["server"]}
    assert names <= {p.stem for p in SNAPSHOTS}
