#!/usr/bin/env python3
"""Parse ShowMeWhy's embedded composition grammar.

This module never invokes Claude Code slash commands. It converts slash-prefixed
stage tokens inside the real /showmewhy command's arguments into a validated
execution plan that the ShowMeWhy skill can execute itself.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
from dataclasses import dataclass
from typing import Iterable


ALIASES = {
    "showmewhy": "verify",
    "verify": "verify",
    "monitor": "monitor",
    "why": "why",
    "compare": "compare",
    "deep": "deep",
    "short": "short",
    "focus": "focus",
    "concise": "focus",
    "i-have-adhd": "focus",
    "impact": "impact",
    "json": "json",
}

PRESENTATION_STAGES = {"why", "short", "focus", "json"}
VERIFICATION_STAGES = {"verify", "deep", "compare"}
STAGE_TOKEN = re.compile(r"^/[a-z0-9][a-z0-9-]*$")


@dataclass(frozen=True)
class Plan:
    stages: tuple[str, ...]
    task: str
    source_tokens: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "stages": list(self.stages),
            "task": self.task,
            "source_tokens": list(self.source_tokens),
        }


class CompositionError(ValueError):
    """Raised when the embedded ShowMeWhy composition grammar is invalid."""


def _normalise_stage(token: str) -> str:
    raw = token[1:] if token.startswith("/") else token
    try:
        return ALIASES[raw]
    except KeyError as exc:
        supported = ", ".join("/" + key for key in sorted(ALIASES))
        raise CompositionError(
            f"unsupported ShowMeWhy stage: {token}. Supported: {supported}"
        ) from exc


def _dedupe_adjacent(items: Iterable[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        if not result or result[-1] != item:
            result.append(item)
    return result


def _validate(stages: list[str]) -> list[str]:
    if not stages:
        return ["verify"]

    if "json" in stages and stages[-1] != "json":
        raise CompositionError("/json must be the final ShowMeWhy stage")

    presentation = [stage for stage in stages if stage in PRESENTATION_STAGES]
    if len(presentation) > 1:
        raise CompositionError(
            "choose only one presentation stage: /why, /short, /focus, or /json"
        )

    verification = [stage for stage in stages if stage in VERIFICATION_STAGES]
    if not verification and not set(stages).issubset({"monitor", "impact"}):
        # Presentation stages require a verification state. Add the ordinary
        # ShowMeWhy verifier rather than asking Claude Code to invoke /showmewhy.
        insert_at = 1 if stages and stages[0] == "monitor" else 0
        stages.insert(insert_at, "verify")

    if "monitor" in stages and stages.index("monitor") != 0:
        raise CompositionError("/monitor must be the first stage when composed")

    if "impact" in stages and stages[-1] not in {"impact", "json"}:
        raise CompositionError(
            "/impact must be the final stage, or immediately before /json"
        )

    return stages


def parse_arguments(raw: str) -> Plan:
    """Parse the arguments supplied after the real `/showmewhy` invocation.

    Composition form::

        /monitor /showmewhy /i-have-adhd -- investigate auth failures

    Legacy ShowMeWhy forms are deliberately left untouched by returning the
    complete text as the task when the first argument is not slash-prefixed::

        why investigate auth failures
    """

    raw = raw.strip()
    if not raw:
        return Plan(("verify",), "", ())

    try:
        tokens = shlex.split(raw)
    except ValueError as exc:
        raise CompositionError(f"invalid ShowMeWhy arguments: {exc}") from exc

    # Composition is opt-in. This preserves the existing mode syntax exactly.
    if not tokens or not STAGE_TOKEN.match(tokens[0]):
        return Plan(("verify",), raw, ())

    delimiter = tokens.index("--") if "--" in tokens else None
    stage_tokens = tokens if delimiter is None else tokens[:delimiter]
    task_tokens = [] if delimiter is None else tokens[delimiter + 1 :]

    if not stage_tokens:
        raise CompositionError("composition requires at least one ShowMeWhy stage")

    for token in stage_tokens:
        if not STAGE_TOKEN.match(token):
            raise CompositionError(
                "use `--` before task text; only /stage tokens are allowed before it"
            )

    stages = _dedupe_adjacent(_normalise_stage(token) for token in stage_tokens)
    stages = _validate(stages)

    return Plan(
        tuple(stages),
        " ".join(task_tokens).strip(),
        tuple(stage_tokens),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parse ShowMeWhy embedded composition arguments"
    )
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    raw = " ".join(args.arguments)

    try:
        plan = parse_arguments(raw)
    except CompositionError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 2

    print(json.dumps({"ok": True, **plan.as_dict()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
