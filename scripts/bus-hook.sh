#!/usr/bin/env bash
# bus-hook.sh — Claude Code hook helper: print unread bus messages (excluding
# Claude's own) and advance the read cursor. stdout is injected into the
# session context, so wiring this as SessionStart + UserPromptSubmit makes the
# bus arrive without anyone typing "check comms".
#
#   scripts/bus-hook.sh            print unread, then mark them read
#   scripts/bus-hook.sh --peek     print unread, leave the cursor alone
#
# Hook snippet: docs/comms/README.md ("auto-delivery on the Claude side").
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BUS="$ROOT/scripts/agentmsg.sh"
CURSOR="$ROOT/docs/comms/.cursor"

peek=0
[[ "${1:-}" == "--peek" ]] && peek=1

last=""
[[ -s "$CURSOR" ]] && last="$(tr -dc '0-9' < "$CURSOR")"
[[ -n "$last" ]] || last=0

raw="$("$BUS" list "$last")"
[[ -n "$raw" ]] || exit 0

unread="$(printf '%s\n' "$raw" | awk -F' \\| ' '$3 != "agnes"')"
if [[ -n "$unread" ]]; then
  echo "## Agent bus — unread messages from buffy"
  echo
  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    id="${line%% | *}"
    "$BUS" show "$id"
    echo
  done <<< "$unread"
  echo "Reply with: scripts/msg-buffy.sh \"subject\" <<'MSG' ... MSG"
fi

if [[ "$peek" -eq 0 ]]; then
  newest="$(printf '%s\n' "$raw" | tail -n 1 | cut -d' ' -f1)"
  printf '%s\n' "$newest" > "$CURSOR"
fi
