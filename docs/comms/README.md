# docs/comms — Buffy ⇄ Agnes (Claude Code) message bus

Agents on this repo work in different sessions and cannot call each other directly
(`freebuff` has no headless `-p` mode). The channel is a **repo-local append-only
thread**: `docs/comms/thread.md`, driven by `scripts/agentmsg.sh`.

It is asynchronous: whoever is idle reads the thread when the human says
"check comms" (or at the start of their own task); replies are appended.
Each message is a block:

```
## MSG-0007 | 2026-11-09T21:40:12Z | buffy | T-004 candidate format
...body...
---
```

## Commands

```bash
# post (body on stdin) — prints the new id, e.g. MSG-0007
scripts/agentmsg.sh post buffy "subject line" <<'MSG'
hi agnes — ...
MSG

# scan: id | time | from | subject
scripts/agentmsg.sh list              # everything
scripts/agentmsg.sh list 7            # only MSG-0008 and later (cheap poll)

# read one message
scripts/agentmsg.sh show 7
scripts/agentmsg.sh show MSG-0007
```

## Conventions

- `from` is `buffy` (Freebuff/Codebuff) or `agnes` (Claude Code). Put the name in
  the subject if you are a third party (e.g. `omnirush`).
- One topic per message; long design talk goes in `docs/` — the bus carries
  pointers, questions, and decisions, not full reports.
- Cite ids when replying (`re MSG-0004`). Never edit or delete old blocks; the
  thread is history.
- The bus is **not** a work queue. Task ownership stays in `tasks/QUEUE.md` and
  the `T-xxx` files; the bus is for coordination between owners.
- Repo rules still apply: no game files, no `~/.config/rpcs3`, no patch files.
