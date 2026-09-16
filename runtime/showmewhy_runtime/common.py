from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


def estimate_tokens(value: Any) -> int:
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if not text:
        return 0
    return max(1, (len(text.encode("utf-8")) + 3) // 4)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_id(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def state_home() -> Path:
    """Return ShowMeWhy's global state directory without touching the cwd.

    `SHOWMEWHY_HOME` is the explicit override for CI, portable installs, or users
    who want ShowMeWhy state on another volume.
    """

    override = os.getenv("SHOWMEWHY_HOME")
    if override:
        return Path(override).expanduser().resolve()

    home = Path.home()
    if os.name == "nt":
        local_app_data = os.getenv("LOCALAPPDATA")
        base = Path(local_app_data).expanduser() if local_app_data else home / "AppData" / "Local"
        return base / "ShowMeWhy"

    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "ShowMeWhy"

    xdg_state = os.getenv("XDG_STATE_HOME")
    base = Path(xdg_state).expanduser() if xdg_state else home / ".local" / "state"
    return base / "showmewhy"


def project_root(cwd: str | Path | None = None) -> Path:
    """Resolve a stable project boundary without executing git.

    A `.git` directory *or file* identifies the root, so git worktrees are
    handled as well as ordinary clones. Outside git, the supplied cwd itself is
    the boundary.
    """

    base = Path(cwd or os.getcwd()).expanduser().resolve()
    if base.is_file():
        base = base.parent

    for candidate in (base, *base.parents):
        if (candidate / ".git").exists():
            return candidate
    return base


def _project_namespace(root: Path) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", root.name).strip("-._") or "project"
    slug = slug[:48]
    digest = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:16]
    return f"{slug}-{digest}"


def runtime_root(cwd: str | Path | None = None) -> Path:
    """Return a project-scoped runtime directory in global ShowMeWhy state.

    Nothing is created inside the consumer repository. Separate projects remain
    isolated by a stable namespace derived from their resolved project root.
    """

    root = state_home() / "projects" / _project_namespace(project_root(cwd))
    root.mkdir(parents=True, exist_ok=True)
    return root
