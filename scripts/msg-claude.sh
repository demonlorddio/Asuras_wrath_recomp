#!/usr/bin/env bash
# msg-claude.sh — Buffy → Claude Code (Agnes) delivery.
#
#   scripts/msg-claude.sh "subject"                    append to the bus only
#   scripts/msg-claude.sh --live "subject"             + send into a Claude session
#   scripts/msg-claude.sh --live --session 3bbdb40a "subject"
#
# Body on stdin. --live resumes a Claude Code conversation with the message and
# appends the reply back to the bus. Target session: --session, else
# $CLAUDE_BUS_SESSION, else the id saved in docs/comms/claude-session; with none
# of those a dedicated "buffy-bus" conversation is created and saved.
# Uses claude-omniroute when present (it wires the local gateway env), else claude.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BUS="$ROOT/scripts/agentmsg.sh"
SID_FILE="$ROOT/docs/comms/claude-session"

live=0
session=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --live) live=1; shift ;;
    --session)
      session="${2:-}"
      [[ -n "$session" ]] || { echo "msg-claude: --session needs an id" >&2; exit 2; }
      shift 2 ;;
    --session=*) session="${1#*=}"; shift ;;
    -h|--help) sed -n '2,13p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    --) shift; break ;;
    -*) echo "msg-claude: unknown option $1" >&2; exit 2 ;;
    *) break ;;
  esac
done

subject="${1:-}"
[[ -n "$subject" ]] || { echo "usage: msg-claude.sh [--live] [--session id] <subject>  (body on stdin)" >&2; exit 2; }
body="$(cat)"
[[ -n "${body//[[:space:]]/}" ]] || { echo "msg-claude: empty body" >&2; exit 2; }

id="$("$BUS" post buffy "$subject" <<<"$body")"
echo "$id"
[[ "$live" -eq 1 ]] || exit 0

assert_cli() {
  local cli
  cli="$(command -v claude-omniroute || command -v claude || true)"
  [[ -n "$cli" ]] || { echo "msg-claude: no claude CLI on PATH — message is on the bus only" >&2; exit 3; }
  printf '%s' "$cli"
}
cli="$(assert_cli)"

if [[ -z "$session" ]]; then
  session="${CLAUDE_BUS_SESSION:-}"
fi
if [[ -z "$session" && -s "$SID_FILE" ]]; then
  session="$(tr -d '[:space:]' < "$SID_FILE")"
fi

prompt="$(cat <<EOF
[message bus $id from buffy]

$subject

$body

Reply briefly and concretely. Later messages to buffy go through
scripts/msg-buffy.sh; the thread is docs/comms/thread.md — cite $id.
EOF
)"

reply_file="$(mktemp)"
trap 'rm -f "$reply_file"' EXIT
timeout_s="${MSG_CLAUDE_TIMEOUT:-180}"
# read-only repo access; plan mode keeps the live session from editing anything
tools="${MSG_CLAUDE_TOOLS:-Read,Grep,Glob}"

if [[ -n "$session" ]]; then
  if ! timeout "$timeout_s" "$cli" -p --resume "$session" --tools "$tools" --permission-mode plan "$prompt" >"$reply_file" 2>&1; then
    echo "msg-claude: could not resume '$session' (message is on the bus, not lost)." >&2
    sed -n '1,6p' "$reply_file" >&2
    exit 3
  fi
else
  session="$(python3 -c 'import uuid;print(uuid.uuid4())')"
  if ! timeout "$timeout_s" "$cli" -p --session-id "$session" -n buffy-bus --tools "$tools" --permission-mode plan "$prompt" >"$reply_file" 2>&1; then
    echo "msg-claude: could not start a bus session (message is on the bus)." >&2
    sed -n '1,6p' "$reply_file" >&2
    exit 3
  fi
  printf '%s\n' "$session" > "$SID_FILE"
fi

# drop CLI banners, gateway warnings and stray blank lines from the captured reply
reply="$(awk '
  /^We.re changing auto mode/ { skip=1; next }
  skip && /^[[:space:]]*$/     { skip=0; next }
  skip                        { next }
  /^[[:space:]]*$/            { next }
  /^\[claude-code:/          { next }
  /Loaded env from/           { next }
  { print }
' "$reply_file")"
[[ -n "$reply" ]] || { echo "msg-claude: empty reply; session $session" >&2; exit 4; }

"$BUS" post agnes "re $id — live reply ($session)" <<<"$reply" >/dev/null
printf -- '--- reply (%s) ---\n%s\n' "$session" "$reply"
