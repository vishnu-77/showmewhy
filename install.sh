#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${SHOWMEWHY_REPO_URL:-https://github.com/vishnu-77/showmewhy.git}"
MARKETPLACE_SOURCE="${SHOWMEWHY_MARKETPLACE_SOURCE:-$REPO_URL}"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
KNOWN_MARKETPLACES="$CLAUDE_HOME/plugins/known_marketplaces.json"
LEGACY_SKILL="$CLAUDE_HOME/skills/showmewhy"

log() {
  printf '%s\n' "$1"
}

if ! command -v claude >/dev/null 2>&1; then
  log "Claude Code not found. Installing Anthropic's stable native build..."
  curl -fsSL https://claude.ai/install.sh | bash -s stable
fi

export PATH="$HOME/.local/bin:$PATH"
if ! command -v claude >/dev/null 2>&1; then
  echo "ShowMeWhy: Claude Code installation was not found on PATH." >&2
  exit 1
fi

export CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1

log "Installing ShowMeWhy..."
claude plugin uninstall showmewhy@showmewhy >/dev/null 2>&1 || true
claude plugin marketplace remove showmewhy >/dev/null 2>&1 || true
claude plugin marketplace add "$MARKETPLACE_SOURCE"

if [[ ! -f "$KNOWN_MARKETPLACES" ]]; then
  echo "ShowMeWhy: Claude marketplace state was not created at $KNOWN_MARKETPLACES." >&2
  exit 1
fi

python3 - "$KNOWN_MARKETPLACES" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
entry = data.get("showmewhy")
if not isinstance(entry, dict):
    raise SystemExit("ShowMeWhy marketplace registration was not found")
entry["autoUpdate"] = True
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY

# Remove the 4.1.0-era copied personal Skill so the marketplace-managed Skill is
# the only source of truth. This prevents the command contract from going stale.
rm -rf "$LEGACY_SKILL"

claude plugin install showmewhy@showmewhy

if ! claude plugin list 2>/dev/null | grep -q 'showmewhy@showmewhy'; then
  echo "ShowMeWhy: plugin is not registered after installation." >&2
  exit 1
fi

python3 - "$KNOWN_MARKETPLACES" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
if data.get("showmewhy", {}).get("autoUpdate") is not True:
    raise SystemExit("ShowMeWhy marketplace auto-update is not enabled")
PY

log ""
log "ShowMeWhy installed with marketplace auto-update enabled."
log "  plugin   showmewhy@showmewhy"
log "  command  /showmewhy"
log "  status   /showmewhy status"
log "  update   /showmewhy update"
log "  updates  automatic after Claude startup when upstream changes"
log ""
log "Restart Claude Code once after this installation."
