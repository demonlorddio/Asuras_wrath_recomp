# docs/comms — Buffy ⇄ Agnes (Claude Code) message bus

Two agents, two sessions, one repo. The channel is an **append-only thread**
(`docs/comms/thread.md`) plus delivery scripts that each side can run.

```
buffy (Freebuff) --msg-claude.sh--> docs/comms/thread.md <--msg-buffy.sh-- agnes (Claude Code)
                        |                                              ^
                        +---- claude -p --resume (live reply) ----------+
```

- **Claude side is real-time-ish**: `msg-claude.sh --live` resumes a Claude Code
  conversation, sends the message, and appends the reply to the thread. Verified
  working through the local omniroute gateway (`claude-omniroute -p --resume`).
- **Buffy side is async**: the Freebuff runtime exposes no headless or send API
  (`freebuff --help` has no `--print`; there is no local IPC socket for a live
  session), so a message lands on the bus and a desktop notification tells the
  human to say **"check comms"** in the Freebuff session.
- **Auto-read on the Claude side is opt-in** via a hook (below): then Claude sees
  unread bus messages at session start and on every prompt, no human relay.

## Thread format

```
## MSG-0007 | 2026-11-09T21:40:12Z | buffy | T-004 candidate format
...body...
---
```

`from` is `buffy` or `agnes`. One topic per message; cite ids when replying;
never edit or delete old blocks.

## Scripts

| Script | Run by | Does |
|---|---|---|
| `scripts/agentmsg.sh post <from> <subject>` | either | append a message, prints `MSG-nnnn` |
| `scripts/agentmsg.sh list [since-id]` | either | `id \| time \| from \| subject` |
| `scripts/agentmsg.sh show <id>` | either | print one message block |
| `scripts/msg-claude.sh [--live] [--session id] "subject"` | buffy | post to the bus; `--live` also delivers into a Claude session and posts the reply |
| `scripts/msg-buffy.sh [--quiet] "subject"` | agnes | post to the bus + desktop notification |
| `scripts/bus-hook.sh [--peek]` | Claude hook | print unread messages (not agnes's own), advance cursor |

Bodies go on **stdin**:

```bash
scripts/msg-buffy.sh "T-004 format confirmed" <<'MSG'
re MSG-0001 — use [type, ppu_vaddr, value], no old value.
MSG
```

### Live Claude delivery

`msg-claude.sh --live` targets the conversation id in `docs/comms/claude-session`
(a dedicated `buffy-bus` conversation, created on first use), or `--session`,
or `$CLAUDE_BUS_SESSION`. It runs `claude-omniroute -p --resume <id>
--tools "Read,Grep,Glob" --permission-mode plan` (plain `claude` fallback) — the
live session can read the repo but not write it — with timeout `$MSG_CLAUDE_TIMEOUT`
(default 180 s). Override the tool set with `$MSG_CLAUDE_TOOLS`. CLI banners and
gateway warnings are stripped before the reply is posted back as `agnes`.
If the resume fails (e.g. that session is busy in a terminal), the message stays
on the bus and the script exits 3 — nothing is lost.

Pointing it at an interactive session is possible (`--session 3bbdb40a`), but a
session that is open in a terminal may refuse to resume; the dedicated bus
conversation is the reliable target.

### Auto-delivery on the Claude side (opt-in)

Add to `.claude/settings.json` (project-scope, so it is trusted with the repo):

```json
{
  "hooks": {
    "SessionStart":     [{ "hooks": [{ "type": "command",
      "command": "\"$CLAUDE_PROJECT_DIR\"/scripts/bus-hook.sh" }] }],
    "UserPromptSubmit": [{ "hooks": [{ "type": "command",
      "command": "\"$CLAUDE_PROJECT_DIR\"/scripts/bus-hook.sh" }] }]
  }
}
```

Hook stdout is added to Claude's context, so unread messages appear without
anyone typing "check comms"; the cursor in `docs/comms/.cursor` prevents repeats.

## Rules

- The bus is coordination, not a work queue: ownership stays in `tasks/QUEUE.md`
  and the `T-xxx` files.
- Long design talk goes in `docs/`; the bus carries pointers, questions, decisions.
- Repo rules still apply: no game files, no `~/.config/rpcs3`, no patch files.
