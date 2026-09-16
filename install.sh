#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${SHOWMEWHY_REPO_URL:-https://github.com/vishnu-77/showmewhy.git}"
MARKETPLACE_SOURCE="${SHOWMEWHY_MARKETPLACE_SOURCE:-$REPO_URL}"
SOURCE_DIR="${SHOWMEWHY_SOURCE_DIR:-}"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
SKILL_DEST="$CLAUDE_HOME/skills/showmewhy"
ARCHIVE_URL="${SHOWMEWHY_ARCHIVE_URL:-https://github.com/vishnu-77/showmewhy/archive/refs/heads/main.tar.gz}"
TMP_DIR=""

cleanup() {
  if [[ -n "$TMP_DIR" && -d "$TMP_DIR" ]]; then
    rm -rf "$TMP_DIR"
  fi
}
trap cleanup EXIT

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

log "Installing ShowMeWhy runtime..."
if claude plugin marketplace list 2>/dev/null | grep -qi 'showmewhy'; then
  claude plugin marketplace update showmewhy >/dev/null 2>&1 || true
else
  claude plugin marketplace add "$MARKETPLACE_SOURCE"
fi

if claude plugin list 2>/dev/null | grep -q 'showmewhy@showmewhy'; then
  claude plugin uninstall showmewhy@showmewhy >/dev/null
fi
claude plugin install showmewhy@showmewhy

if [[ -n "$SOURCE_DIR" ]]; then
  SKILL_SOURCE="$SOURCE_DIR/standalone/showmewhy"
else
  TMP_DIR="$(mktemp -d)"
  curl -fsSL "$ARCHIVE_URL" -o "$TMP_DIR/showmewhy.tar.gz"
  tar -xzf "$TMP_DIR/showmewhy.tar.gz" -C "$TMP_DIR"
  SKILL_SOURCE="$(find "$TMP_DIR" -type d -path '*/standalone/showmewhy' -print -quit)"
fi

if [[ -z "${SKILL_SOURCE:-}" || ! -f "$SKILL_SOURCE/SKILL.md" ]]; then
  echo "ShowMeWhy: standalone Skill source was not found." >&2
  exit 1
fi

log "Installing /showmewhy globally..."
mkdir -p "$(dirname "$SKILL_DEST")"
rm -rf "$SKILL_DEST"
cp -R "$SKILL_SOURCE" "$SKILL_DEST"

if [[ ! -f "$SKILL_DEST/SKILL.md" ]]; then
  echo "ShowMeWhy: global Skill installation failed." >&2
  exit 1
fi
if ! grep -q '^name: showmewhy$' "$SKILL_DEST/SKILL.md"; then
  echo "ShowMeWhy: installed Skill failed its identity check." >&2
  exit 1
fi
if ! claude plugin list 2>/dev/null | grep -q 'showmewhy@showmewhy'; then
  echo "ShowMeWhy: runtime plugin is not registered after installation." >&2
  exit 1
fi

log ""
log "ShowMeWhy installed."
log "  command  /showmewhy"
log "  skill    $SKILL_DEST"
log "  runtime  showmewhy@showmewhy"
log ""
log "Start a new Claude Code session and type /showmewhy."
