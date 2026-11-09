#!/usr/bin/env bash
# agentmsg.sh — repo-local message bus for the agents working this repo
# (buffy = Freebuff/Codebuff, agnes = Claude Code). Append-only, flock-protected.
#
#   scripts/agentmsg.sh post <from> <subject>   body on stdin -> prints MSG-id
#   scripts/agentmsg.sh list [since-id]         one line per message after since-id
#   scripts/agentmsg.sh show <id>               full message block
#
# Thread lives at docs/comms/thread.md; protocol in docs/comms/README.md.
set -euo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DIR="$(dirname -- "$HERE")/docs/comms"
THREAD="$DIR/thread.md"
LOCK="$DIR/.thread.lock"

mkdir -p "$DIR"
if [[ ! -f "$THREAD" ]]; then
  cat > "$THREAD" <<'EOF'
# Agent message bus

Append-only thread. Post with `scripts/agentmsg.sh post <from> <subject>` (body on
stdin); read with `list` / `show <id>`. One topic per message; cite MSG-ids when
replying. Protocol: `docs/comms/README.md`.
EOF
fi

last_id() {
  local id
  id="$(grep -oE '^## MSG-[0-9]+' "$THREAD" | tail -n 1 | grep -oE '[0-9]+' || true)"
  printf '%s' "${id:-0}"
}

cmd="${1:-}"
shift 2>/dev/null || true

case "$cmd" in
  post)
    from="${1:?usage: agentmsg.sh post <from> <subject>  (body on stdin)}"
    subject="${2:?usage: agentmsg.sh post <from> <subject>  (body on stdin)}"
    body="$(cat)"
    if [[ -z "${body//[[:space:]]/}" ]]; then
      echo "agentmsg: empty body — pass the message on stdin" >&2
      exit 1
    fi
    exec 9>"$LOCK"
    flock -w 10 9
    id="$(printf '%04d' "$(( $(last_id) + 1 ))")"
    ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    {
      printf '## MSG-%s | %s | %s | %s\n\n%s\n\n---\n\n' "$id" "$ts" "$from" "$subject" "$body"
    } >> "$THREAD"
    flock -u 9
    echo "MSG-$id"
    ;;
  list)
    since="$(printf '%s' "${1:-0}" | grep -oE '[0-9]+' || echo 0)"
    awk -v since="$((10#${since:-0}))" '
      /^## MSG-/ {
        line = $0; sub(/^## MSG-/, "", line)
        n = split(line, a, " \\| ")
        if (n >= 4) { id = a[1] + 0; if (id > since) printf "%s | %s | %s | %s\n", a[1], a[2], a[3], a[4] }
      }' "$THREAD"
    ;;
  show)
    want="${1:?usage: agentmsg.sh show <id>}"
    want="${want#MSG-}"
    want="$(printf '%s' "$want" | grep -oE '[0-9]+' || true)"
    if [[ -z "$want" ]]; then
      echo "agentmsg: need a numeric id (e.g. 7 or MSG-0007)" >&2
      exit 1
    fi
    awk -v want="$((10#${want}))" '
      /^## MSG-/ {
        line = $0; sub(/^## MSG-/, "", line)
        split(line, a, " \\| "); on = (a[1] + 0 == want)
      }
      on { print }
      on && /^---$/ { exit }
    ' "$THREAD"
    ;;
  *)
    sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    exit 1
    ;;
esac
