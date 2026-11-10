# Briefing for claude-code (taking over the Agnes lane)

Paste this whole file into Claude Code as its first message. It summarises work that is
already finished and verified. Treat the numbers and addresses below as established
facts — they are backed by the RPCS3 log, the disassembly or a boot test. Do not
re-derive them, and do not replace them with guesses.

---

## 1. The project

`/home/dio/Projects/Asuras_wrath_recomp` — Asura's Wrath (**BLUS30721**, PS3, USA) on a
native PPU recompilation rather than JIT emulation. Public repo
`demonlorddio/Asuras_wrath_recomp`, branch `master`.

Read, in this order:

- `docs/NATIVE-PLAN.md` — plan, root causes R1–R7, options A/B/D, phases
- `docs/DEEP-DIVE.md` — disc, `rom_data` and cache analysis
- `docs/CHEAT-SPECS.md` — per-cheat spec (only the 60fps row is final)
- `docs/t005-frame-pacing.md` — frame pacing: what was measured and what a measurement
  is allowed to mean
- `tasks/QUEUE.md` — the master board; `tasks/T-00x.md` — self-contained task briefs
- `paths.env` — absolute paths to everything **outside** the repo

Team: **you** (architect, merge gates), **Freebuff** (throughput; T-004, T-005, and
T-006 in progress), **Omnirush** (D2/D3, on maintenance for a few days).

## 2. Rules that are not negotiable

1. **No game files** in git or in any release: no `disc_extracted/`, no
   `rom_data/*.ppumod`, no EBOOT, no keys. The compiled module is derived from the
   player's own disc and stays on their machine.
2. **Never invent an address.** R4 was fabricated addresses; a patch ships only with
   its derivation (byte evidence + disassembly + a boot that shows the effect). A
   wrong address can crash the game.
3. **The launcher regenerates the live patch files on every Play press.** A
   hand-edited `~/.config/rpcs3/patches/patch.yml` is wiped before the engine boots.
   Edit `CHEAT_LINES` / `PROBE_LINES` in the launcher instead.
4. **Repo-local findings**: `re/`, `docs/`, `tasks/`. `~/.config/rpcs3/*` and the
   launcher folder are yours to *operate*; the source of truth is the repo.
5. **One branch per task**, the task file is the spec, flip your `Status:` line, and
   leave a report section at the bottom of the task file.
6. **Nothing is pushed** unless the user asks. No local remote is configured yet.
7. **Don't wire an empty cheat slot.** Six slots have no verified address; the
   launcher emits no patch block for them, and that stays true until an address lands
   with its derivation.

## 3. Where things physically live

From `paths.env`:

| What | Path |
| --- | --- |
| Package / launcher | `/home/dio/Games/AsurasWrathRecomp-linux-x86_64` |
| Program (Python/tkinter) | `<pkg>/asuraswrath`, always launch from inside `<pkg>` |
| Engine (RPCS3 fork) | `<pkg>/engine/rpcs3` |
| Compiled PPU module | `<pkg>/rom_data/BLUS30721.ppumod` (59 MB) + `.manifest.json` |
| Extracted disc | `<pkg>/disc_extracted/PS3_GAME/...` |
| Engine config | `~/.config/rpcs3/config.yml` |
| Patch enable bookkeeping | `~/.config/rpcs3/patch_config.yml` |
| Generated patches | `~/.config/rpcs3/patches/patch.yml` |
| Patch state | `~/.config/rpcs3/patches_state.json` |
| Engine log | `~/.cache/rpcs3/RPCS3.log` |
| Saves | `~/.config/rpcs3/dev_hdd0/home/00000001/savedata` |

Patch container key (live, from the log): `PPU-83096111daff850cc92b637aec1780c4079e1c58`.
It is SHA1 over the EBOOT LOAD segments; `All`/serial keys are wrong for this build.

## 4. Git state, as of now

```
911f8b7 release: package the launcher with its RecompLauncher manifest, and say how to play
74cb32b RecompLauncher: one-click setup and settings for the recomp
c49bda0 comms: snapshot MSG-0024 (P2 finalized + boot-verified; T-006 plan absorbed)
f4026f2 P2 finalized: 60FPS Unlock ships both lines (target + pace scale)
6fd9451 comms: snapshot MSG-0016..MSG-0023 (T-005 merge, P1/P2 rounds, T-006 claim + census)
c64b59d T-006: no cheat hooks ship in this build, so the six slots need the damage path
395ddb4 queue: P2 confirmed (title caps at 60); extras slot wired; T-006 = six slots
```

- The repo is public and on GitHub; `origin` = `demonlorddio/Asuras_wrath_recomp`
  was configured 2026-11-10, `master` is pushed (tip `911f8b7`), and the first
  release, **v0.9.0** (prototype), carries the tarball from
  `scripts/package_release.sh`.
- `recomplauncher-agent.md` in the repo root is an untracked copy of the RecompLauncher
  SDK guide, byte-identical to the live one at
  https://recomplauncher.com/sdk-files/recomplauncher-agent.md. Leave it untracked.
- `docs/comms/thread.md` is the agent message bus. Append only; `scripts/agentmsg.sh post <from> "<subject>"`
  with the body on stdin.

## 5. Verified technical state

### 5.1 Patch pipeline (working, boot-verified)

`Version: "1.2"` at the top of `patch.yml`, the PPU hash as the container key, and
`patch_config.yml` carrying `Enabled: true` per patch. Boot markers in `RPCS3.log`:
the probe applies as `<- 1`, the 60fps block as `<- 2`, the hash line as `<- 3`, with
zero `PAT: Error` and zero `Skipping`.

Syntax gotcha: `bef32`/`lef32` take a **decimal float** in YAML (`60.0`,
`500000.0`). A hex word like `0x42700000` makes yaml-cpp fail and the whole block is
skipped (`bin_patch.cpp:808`). `be32` does take `0x` hex.

### 5.2 Frame pacing — P2 is final, do not re-tune

- `0x19afbac` = `60.0f` — the frame-rate **target** the game loop consumes.
- `0x8a9438` = `1,000,000.0f` natively (`49 74 24 00`), the seconds→µs **pace scale**
  in the shared sleep helper. Exactly **one reader**: `lfs 2, 0(3)` at `0x8a9470`,
  with the base built at `0x8a9464`/`0x8a946c`. One reader means it scales all ~70
  sleep sites (title, menus, gameplay, IO) — it is **not** title-only.
- Shipped value `500000.0`: a `sleep(1/30)` round trip becomes 16667 µs = one 60fps
  frame. Both lines ship together inside the single `cheat_60fps` toggle. Boot-verified:
  title now reads av 54.7 / mx 60.0; gameplay was already ~60 (av 57.9).
- `0x166c9b8` next to it is the **2^63 round-half-up constant**, not 0.5. Never touch.
- `0x160bbf0` is double `4294967296.0` (timebase scaler). Never touch.
- Known side effect, accepted: anything paced by a *different* constant now runs 2× fast.
  Watch animation/audio speed in one cutscene.
- Method rule from T-005: an fps number only counts if the probe is confirmed in the log
  (`probe <- N`) **and** the hash changed first. The framerate-box `av:` is the routing
  number, not proof.

### 5.3 Cheats — the census (T-006), which changes the plan

The cooked binary keeps its UnrealScript names: **2,396 `<Class>exec<Func>` records**
survive (name table around `0x162fe41`). The complete `UCheatManager` set is **navmesh
debug only**: DumpCoverStats, VerifyNavMeshCoverRefs, PrintNavMeshObstacles,
PrintAllPathObjectEdges, DrawUnsupportingEdges, VerifyNavMeshObjects,
LogParticleActivateSystemCalls, LogPlaySoundCalls.

There is **no `execGod`, `execGhost`, `execAllAmmo` or any gameplay cheat**. The only
`Unlock*` records are achievements/trophies. So: a console-cheat route and a
"cheats enabled" flag are both dead on this disc.

Per-slot reachability:

- **god + one_shot** — ONE investigation, not two: the damage path (TakeDamage /
  CanBeDamaged branch). `one_shot` also needs the damage multiplier from there.
- **skip_intro** — reachable code-side. Bink natives exist (`PlayMovie`, `StopMovie`,
  `IsMoviePlaying`, `IsMovieFinish`, `SetInput`). But there are **zero** `.bik`/`intro`/
  `logo` strings in the EBOOT: the intro is Kismet/sequence-driven, so there is no
  movie name to patch.
- **heavy** — promising: `ABCPlayerController_HeavyShoot` is its own PlayerController
  class, so the cooldown is a field on it (a stable data address is plausible).
- **burst** — the gauge is a per-frame updated component field; likely a field, not a
  constant.
- **extras** — **probably not in the module at all.** No extras/gallery/artwork
  strings; the only unlock surface is achievements. Reads like save-profile data, i.e.
  a profile edit, not a patch. Tell the user that rather than ship a guess.
- **SPU angle is dropped**: the disc is a single PPU module with 0 `.sprx`, so there is
  no separate SPU image to sweep.

T-004's `.rodata` sweep is negative for all of these, and `re/candidates.csv` (4,585
hits) covers only float constants — consistent with state machines living in
heap/objects, not `.rodata`.

## 6. New track since MSG-0024: RecompLauncher support

The user asked for RecompLauncher support (guide: `recomplauncher-agent.md`). Done and
committed:

- **`recomplauncher.json`** (repo root, level 1 + 2 + `prepare`): `game` asks for the
  ISO or the `PS3_GAME` folder and checks `PS3_GAME/PARAM.SFO`; `start` is
  `asuraswrath --game {game}`; `prepare` runs `asuraswrath --prepare --game {game}`
  (the one-time 5–15 min compile, with `progress N text` lines); settings write the
  keys the launcher actually reads (resolution, frame-rate unlock, refresh, window,
  V-Sync, upscaling, overlay); `saves` is RPCS3's `dev_hdd0/.../savedata`; `exit_codes`
  2 and 3. Schema-validated. `game.dumps` is deliberately absent: no Redump CRC32 was
  verifiable, and a wrong one mislabels good discs.
- **`asuraswrath` gained `--game PATH`, `--prepare`, `--dry-run`, `--version`** (plus
  the bare positional path its own README already promised). Headless runs reuse the
  existing `apply_settings()`/`write_patches()` code; no arguments still opens the GUI
  exactly as before (smoke-tested, no stderr). `--prepare` skips the compile when the
  module was already built from that same copy.
- **Important:** that launcher change lives in the package folder, **not in git** —
  there is no launcher source in this repo. Backup: `<pkg>/asuraswrath.bak4`. If you
  change the launcher, diff against that backup and keep the flags working, because
  `recomplauncher.json` depends on them.
- **`scripts/package_release.sh`** builds
  `AsurasWrathRecomp-<ver>-Linux-x86_64.tar.gz` with `recomplauncher.json` at the top
  next to the program, and excludes `disc_extracted/`, `rom_data/*.ppumod`,
  `settings.json`, `recomp.cfg`. Tested: extracted elsewhere, `--version` and
  `--dry-run` work from the extracted copy.
- **README** gained the badge (linking to recomplauncher.com — this recomp is *not* in
  the catalog; the only "Asura's Wrath" entry there is PauloUbirajara's Xbox 360
  ReXGlue project) and a "How to play" section.

Open on that track: no tagged release exists yet, and the clone has no `origin`, so
`recomplauncher.json` cannot reach a player until a release carries it.

## 7. What to do next, in order

1. **T-006 damage-path trace** (god + one_shot, including the multiplier). Freebuff is
   working this; do not duplicate it — review what lands and gate it.
2. **skip_intro** via the Bink/Kismet skip flag; **heavy** via the
   `ABCPlayerController_HeavyShoot` fields; **burst** via the gauge field.
3. **extras**: keep it unwired and tell the user it is a save-profile edit.
4. **Release the RecompLauncher manifest** — done as **v0.9.0** on 2026-11-10
   (prototype number chosen over 1.2.0; the next release picks up the number).
5. Standards still open (see the report in `recomplauncher-agent.md`): no PAL/USA check,
   ISO copies cannot be identity-checked by the launcher (PS3 images are UDF and the
   schema has no UDF check), six GUI cheat toggles do nothing, `RECOMPLAUNCHER_MODE`/
   `RECOMPLAUNCHER_PAD` unread, Linux-only builds, no Recomp Achievements.

## 8. How to verify anything before claiming it

- Boot and read `~/.cache/rpcs3/RPCS3.log`: the hash line, then `<- N` apply counters,
  and the absence of `PAT: Error` / `Skipping`. Delete the log header or note the boot
  timestamp first, so old lines cannot be mistaken for new ones.
- Check the bytes you patch in `re/disasm/seg_*.bin` (vaddr = file offset + 0x10000 for
  seg 0), not from memory.
- The Python launcher is the only place patch lines come from; if a live file differs
  from `CHEAT_LINES`, the file was hand-edited and will be wiped.

## 9. Reporting

- Findings land in `re/` or `docs/`, task reports at the bottom of `tasks/T-00x.md`,
  board updates in `tasks/QUEUE.md`.
- Bus: `scripts/agentmsg.sh post <from> "<subject>"` with the body on stdin.
- Commits: one or two sentences on *why*, and the footer
  `🤖 Generated with Codebuff` / `Co-Authored-By: Codebuff <noreply@codebuff.com>`
  unless the user says otherwise.
