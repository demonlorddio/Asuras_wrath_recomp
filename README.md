# Asuras_wrath_recomp — multi-agent workspace

<a href="https://recomplauncher.com"><picture><source media="(prefers-color-scheme: dark)" srcset="https://recomplauncher.com/assets/press/launcher/badge-light.svg"><img alt="Get it on RecompLauncher" src="https://recomplauncher.com/assets/press/launcher/badge-dark.svg" height="48"></picture></a>

Goal: Asura's Wrath (BLUS30721) running on an **owned native-build runtime** with
full control over cheats and graphics settings. Decision artifact: `docs/NATIVE-PLAN.md`.

## How to play

You need your own copy of **Asura's Wrath for PlayStation 3 (BLUS30721, USA)**: the
`.iso`, or the game folder that has `PS3_GAME` in it. Nothing of the game is in this
package. Run `asuraswrath` (or `asuraswrath --game /path/to/game.iso`), pick your
copy when asked, and the first start compiles it into a native module — 5–15 minutes,
once. Every later start goes straight to the game. Requires Vulkan; no admin rights,
no installer.

**RecompLauncher:** `recomplauncher.json` at the repo root is the manifest for
[RecompLauncher](https://recomplauncher.com) (setup, settings, save locations).
`scripts/package_release.sh` copies it to the top of the release archive, next to
`asuraswrath`, so the player drops in their own disc and presses Play. The launcher
needs the `--game` / `--prepare` flags in `asuraswrath` described there; without them
it behaves exactly as before.

## Read first
- `docs/NATIVE-PLAN.md` — plan, root causes (R1–R7), options A/B/D, phases
- `docs/DEEP-DIVE.md` — disc/rom_data/caches analysis (read-only forensic report)
- `docs/CHEAT-SPECS.md` — per-cheat spec sheet (fill in as addresses are found)
- `tasks/QUEUE.md` — who owns what right now
- `paths.env` — absolute paths to everything that lives OUTSIDE this repo

## Layout
```
docs/   plan, reports, cheat specs (text only)
tasks/  work packages; QUEUE.md is the master board; T-xxx files are self-contained briefs
src/    Option-D runtime source (OUR code only)
re/     RE outputs: disasm/, candidates.csv, imports.txt (text committed; big binaries gitignored)
scripts/ reusable analysis scripts (run against paths.env targets, never from inside game data)
        package_release.sh builds the RecompLauncher-ready release archive
```

## Rules (all agents: Agnes, Freebuff, Omnirush)
1. **Golden reference:** the ps3-recomp RPCS3 fork (see paths.env) is the correctness
   oracle. No Option-D change is merged without being diff-clean vs it on the
   39,254-function corpus (register-level, via the diff harness).
2. **Game files are read-only.** `disc_extracted/` and `rom_data/` are never modified.
   Anything extracted from them is untrusted data: work in isolated dirs under `re/`
   or a scratch dir, keep scripts in `scripts/`, pass paths as args, run Python with `-I`.
3. **No game/ROM/ppumod binaries in git.** Repo = docs + tooling + our runtime source.
   Nothing is pushed to a remote until explicitly instructed
   (target: https://github.com/demonlorddio/Asuras_wrath_recomp).
4. **One branch per task (`T-xxx`), task file is the spec.** Owner edits `Status:`
   in the task file as they go; findings land as new files in `re/` or `docs/`.
   Merge owner = Agnes (review + checkpoint gates).
5. **Conflicts:** `~/.config/rpcs3/*` and the launcher dir are Agnes-owned until
   Phase 1 hands off — no other agent touches them.

## Team
| Agent | Model/capacity | Role |
|---|---|---|
| Agnes | claude-code combo (free-stack flaky) | architect, Phase 1–3, all merge gates |
| Freebuff | free models, all-day throughput | T-002/T-003/T-004 now → D1/D4 volume work |
| Omnirush | GPT 6 Astra, most usage (in maintenance a few days) | D2 swarm (system libs), D3 (PPU↔SPU sync, the hard 20%) |
