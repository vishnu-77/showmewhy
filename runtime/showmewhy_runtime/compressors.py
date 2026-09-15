from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .common import estimate_tokens


@dataclass(frozen=True)
class CompressionResult:
    kind: str
    text: str
    status: str
    findings: list[str]
    metrics: dict[str, int | float | str]
    parser: str
    confidence: str
    complete: bool


PYTEST_SUMMARY = re.compile(r"(?P<failed>\d+) failed(?:, (?P<passed>\d+) passed)?", re.I)
PYTEST_PASS = re.compile(r"(?P<passed>\d+) passed", re.I)
JEST_SUMMARY = re.compile(r"Tests:\s*(?:(?P<failed>\d+) failed,\s*)?(?:(?P<passed>\d+) passed,\s*)?(?P<total>\d+) total", re.I)
TS_ERROR = re.compile(r"^(?P<path>[^\n:]+(?:\.[jt]sx?))\((?P<line>\d+),(?P<col>\d+)\): error TS(?P<code>\d+): (?P<msg>.+)$")
LINT_LINE = re.compile(r"^(?P<path>[^:\n]+):(?P<line>\d+):(?P<col>\d+):\s*(?P<level>error|warning)\s+(?P<msg>.+)$", re.I)


def _lines(text: str) -> list[str]:
    return [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]


def _compact_findings(lines: list[str], *, limit: int = 14) -> list[str]:
    needles = ("error", "failed", "failure", "exception", "traceback", "warning", "warn", "denied", "vulnerab", "critical")
    out: list[str] = []
    seen: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if any(n in stripped.lower() for n in needles):
            clipped = stripped[:500]
            if clipped not in seen:
                seen.add(clipped)
                out.append(clipped)
        if len(out) >= limit:
            break
    return out


def compress_text(text: str, *, target_tokens: int = 700) -> CompressionResult:
    raw_tokens = estimate_tokens(text)
    if raw_tokens <= target_tokens:
        return CompressionResult("generic", text, "unknown", [], {"raw_tokens": raw_tokens}, "passthrough", "high", True)

    lines = _lines(text)
    joined = "\n".join(lines)

    for line in reversed(lines):
        match = PYTEST_SUMMARY.search(line)
        if match:
            failed = int(match.group("failed"))
            passed = int(match.group("passed") or 0)
            findings = _compact_findings(lines)
            body = [f"pytest: {failed} failed, {passed} passed"]
            if findings:
                body += ["Key failures:"] + [f"- {x}" for x in findings]
            body.append("Raw details retained by ShowMeWhy.")
            return CompressionResult("test", "\n".join(body), "failed" if failed else "passed", findings, {"failed": failed, "passed": passed, "raw_tokens": raw_tokens}, "pytest", "high", True)

    for line in reversed(lines):
        match = PYTEST_PASS.search(line)
        if match and "failed" not in joined.lower():
            passed = int(match.group("passed"))
            return CompressionResult("test", f"pytest: {passed} passed. Raw details retained by ShowMeWhy.", "passed", [], {"passed": passed, "raw_tokens": raw_tokens}, "pytest", "high", True)

    for line in reversed(lines):
        match = JEST_SUMMARY.search(line)
        if match:
            failed = int(match.group("failed") or 0)
            passed = int(match.group("passed") or 0)
            total = int(match.group("total"))
            findings = _compact_findings(lines)
            body = [f"tests: {failed} failed, {passed} passed, {total} total"]
            if findings:
                body += ["Key failures:"] + [f"- {x}" for x in findings]
            body.append("Raw details retained by ShowMeWhy.")
            return CompressionResult("test", "\n".join(body), "failed" if failed else "passed", findings, {"failed": failed, "passed": passed, "total": total, "raw_tokens": raw_tokens}, "jest-vitest", "high", True)

    ts_errors = []
    for line in lines:
        match = TS_ERROR.match(line.strip())
        if match:
            ts_errors.append(f"{match.group('path')}:{match.group('line')} TS{match.group('code')} {match.group('msg')}")
    if ts_errors:
        shown = ts_errors[:16]
        body = [f"TypeScript: {len(ts_errors)} error(s)"] + [f"- {x}" for x in shown]
        if len(ts_errors) > len(shown):
            body.append(f"- … {len(ts_errors)-len(shown)} more in raw evidence")
        return CompressionResult("build", "\n".join(body), "failed", shown, {"errors": len(ts_errors), "raw_tokens": raw_tokens}, "tsc", "high", len(ts_errors) <= len(shown))

    lint = []
    for line in lines:
        match = LINT_LINE.match(line.strip())
        if match:
            lint.append(f"{match.group('level').upper()} {match.group('path')}:{match.group('line')}:{match.group('col')} {match.group('msg')}")
    if lint:
        shown = lint[:18]
        errors = sum(1 for x in lint if x.startswith("ERROR"))
        warnings = len(lint) - errors
        body = [f"lint: {errors} error(s), {warnings} warning(s)"] + [f"- {x}" for x in shown]
        if len(lint) > len(shown):
            body.append(f"- … {len(lint)-len(shown)} more in raw evidence")
        return CompressionResult("lint", "\n".join(body), "failed" if errors else "warning", shown, {"errors": errors, "warnings": warnings, "raw_tokens": raw_tokens}, "lint", "medium", len(lint) <= len(shown))

    if "diff --git " in joined:
        files = [line[11:].split(" b/", 1)[0] for line in lines if line.startswith("diff --git a/")]
        additions = sum(1 for line in lines if line.startswith("+") and not line.startswith("+++"))
        deletions = sum(1 for line in lines if line.startswith("-") and not line.startswith("---"))
        listed = files[:12]
        body = [f"git diff: {len(files)} file(s), +{additions}/-{deletions}"] + [f"- {x}" for x in listed]
        if len(files) > len(listed):
            body.append(f"- … {len(files)-len(listed)} more file(s) in raw evidence")
        return CompressionResult("git", "\n".join(body), "changed", listed, {"files": len(files), "additions": additions, "deletions": deletions, "raw_tokens": raw_tokens}, "git-diff", "high", True)

    findings = _compact_findings(lines)
    head = [x for x in lines[:8] if x.strip()]
    tail = [x for x in lines[-8:] if x.strip()]
    selected: list[str] = []
    for line in head + findings + tail:
        clipped = line[:500]
        if clipped and clipped not in selected:
            selected.append(clipped)
    digest = ["ShowMeWhy compacted verbose tool output."] + selected[:28]
    digest.append("Raw details retained by ShowMeWhy; digest is incomplete.")
    return CompressionResult("generic", "\n".join(digest), "unknown", findings, {"raw_tokens": raw_tokens}, "bounded-log", "low", False)


def response_text(tool_name: str, response: Any) -> str | None:
    if not isinstance(response, dict):
        return None
    if tool_name == "Bash" and isinstance(response.get("stdout"), str):
        stderr = response.get("stderr") if isinstance(response.get("stderr"), str) else ""
        return response["stdout"] + ("\n" + stderr if stderr else "")
    return None


def replace_response_text(tool_name: str, response: Any, new_text: str) -> Any | None:
    if not isinstance(response, dict) or tool_name != "Bash" or not isinstance(response.get("stdout"), str):
        return None
    out = dict(response)
    out["stdout"] = new_text
    return out
