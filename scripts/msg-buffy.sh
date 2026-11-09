#!/usr/bin/env bash
# msg-buffy.sh — Claude Code (Agnes) → Buffy delivery.
#
#   scripts/msg-buffy.sh "subject"            append to the bus + desktop ping
#   scripts/msg-buffy.sh --quiet "subject"    append silently
#
# Body on stdin. Buffy has no local IPC (the Freebuff runtime exposes no
# headless/send API), so delivery is: bus entry + a desktop notification that
# tells the human to say "check comms" in the Freebuff session.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BUS="$ROOT/scripts/agentmsg.sh"

quiet=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --quiet) quiet=1; shift ;;
    -h|--help) sed -n '2,9p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    --) shift; break ;;
    -*) echo "msg-buffy: unknown option $1" >&2; exit 2 ;;
    *) break ;;
  esac
done

subject="${1:-}"
[[ -n "$subject" ]] || { echo "usage: msg-buffy.sh [--quiet] <subject>  (body on stdin)" >&2; exit 2; }
body="$(cat)"
[[ -n "${body//[[:space:]]/}" ]] || { echo "msg-buffy: empty body" >&2; exit 2; }

id="$("$BUS" post agnes "$subject" <<<"$body")"
echo "$id"

if [[ "$quiet" -eq 0 ]] && command -v notify-send >/dev/null 2>&1; then
  notify-send -a "agent bus" "$id from agnes (Claude Code)" \
    "$subject — in Freebuff say: check comms" >/dev/null 2>&1 || true
fi

echo "delivery: in the Freebuff session say \"check comms\" (unread: $id)" >&2
