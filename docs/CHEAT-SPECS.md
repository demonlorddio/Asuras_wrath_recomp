# Cheat spec sheet — Asura's Wrath (BLUS30721)

Single PPU module (0 .sprx on disc) → all game logic lives in EBOOT.BIN
(patch container key `PPU-83096111daff850cc92b637aec1780c4079e1c58`, live from RPCS3.log).
The addresses in the current `patch.yml` are fabricated (root cause R4); the
real ones below come from the T-004 sweep (`re/candidates.csv`) + T-002 disasm.
Only `cheat_60fps` has a candidate so far; everything else is still `TBD`
because those values do not live in `.rodata` (see the T-004 note below).

Constant encodings (PPU is big-endian, verified against `struct.pack`):
30.0f = `0x41F00000`, 60.0f = `0x42700000`, 120.0f = `0x42F00000`,
1/30 s float = `0x3D088889`, 1/60 s float = `0x3C888889`,
30.0 double = `0x403E000000000000`, 60.0 double = `0x404E000000000000`.
(The earlier values here — `0x42F00000` as 30.0f, `0x3D2AAAAB` as 1/30 — were
wrong by a factor of two or more; corrected in T-004, see
`docs/candidates-rationale.md` §1. `0x3D2AAAAB` is 1/24 and `0x3E2AAAAB` is 1/6.)

| Cheat (settings.json key) | Hypothesis | Type | Address | Old → New | In-game verify | State |
|---|---|---|---|---|---|---|
| cheat_60fps | frame-cap float + pace scale | be32/bef32 ×2 | `0x19afbac` + `0x0008a9438` | 0x41F00000 (30.0f) → 0x42700000 (60.0f); 0x49742400 (1e6f) → 0x48F42400 (5e5f) | title/boot loop caps at 60 (av 54.7 / mx 60.0, user HUD 2026-11-10) | **patched (finalized)** |
| cheat_skip_intro | intro-skip flag / movie branch | be32 | TBD — code-side via Bink natives (`SetInput`/`IsMovieFinish`); intro is Kismet-driven, no movie name in EBOOT | ? | skips intro | T-006 tracing |
| cheat_one_shot | damage multiplier / one-hit threshold | be32 | TBD — damage-path trace (one investigation with god, T-006) | ? | enemies die in one hit | T-006 tracing |
| cheat_heavy (+ _cooldown off) | heavy-attack damage/cooldown constant | be32 | TBD — cooldown is a **field** on its own class `ABCPlayerController_HeavyShoot` | ? | heavy blow kills faster | T-006 tracing |
| cheat_burst (+ infinite_burst) | burst gauge cap/refill rate | be32 | TBD — gauge is a per-frame component field | ? | gauge stays full / refills | T-006 tracing |
| cheat_god | invincibility flag | be32 | TBD — no cheat hook ships; player damage-entry branch (called from PC tick/hit resolution), not a global | ? | damage taken = 0 | T-006 tracing |
| cheat_extras / all_extras | extras/cutscene gates | be32 | **probably not in the module** — no extras/gallery/artwork strings; only achievement unlock execs; reads like save-profile data | ? | extra content available | **wrong layer — profile edit, not a patch (T-006)** |

T-004 sweep outcome (see `docs/candidates-rationale.md`):
- `cheat_60fps` is the only slot with a `.rodata` candidate. `0x19afbac` is the
  single address whose code context shows 30.0f being passed as a *value*
  (`lwz 4, -1108(2)` → `bl 0xf31c58` → `cmpwi`); the three alternatives are
  tuning pools with no proven reader. Confidence is low–medium: no data
  constant is proven to be the cap, and 82 of 86 hits are code-side.
- `0x160bbf0` is a **decoy** — 117 `lfd` readers, but the record is the double
  2^32 and the 30.0f bytes are its high half. Do not patch it.
- Every other slot stays `TBD` on purpose: those values live in runtime/heap
  objects or state machines, not `.rodata`. Filling them with a guess would
  repeat root cause R4.

Per-cheat rule: patch **data**, not code — data survives the ppumod precompile
(verify empirically at Phase 1 probe; if constant-folded, bake the value into
EBOOT and rerun `--ppumod-build` instead — see NATIVE-PLAN §2/§8, D-line "bake").

Status column values: `candidate` → `patched` (runtime patch.yml entry) →
`baked` (value in EBOOT + ppumod rebuilt) → `verified` (in-game evidence in qa/).

## T-006 census (2026-11-10, branch `T-006` @c64b59d)

The cooked binary keeps its UnrealScript names: **2,396 `<Class>exec<Func>`
records survive**. CheatManager's complete shipped set is nav-mesh debugging
only (`DumpCoverStats`, `VerifyNavMeshCoverRefs`, `PrintNavMeshObstacles`,
`PrintAllPathObjectEdges`, `DrawUnsupportingEdges`, `VerifyNavMeshObjects`,
`LogParticleActivateSystemCalls`, `LogPlaySoundCalls`). There is **no**
`execGod`/`execGhost`/`execAllAmmo`/any gameplay cheat — the only `Unlock*`
records are achievement/trophy execs. Consequences:

- `god` + `one_shot` **cannot** be done by triggering a cheat function (none
  exists) or flipping a cheats-enabled flag (no cheat subsystem). They must
  come from the damage path itself — one investigation, not two sweeps. The
  next step is the `TakeDamage`/`CanBeDamaged` branch trace; the player's
  damage entry is the one called from the PC's tick/hit resolution, so patch
  that branch, not a global. `one_shot`'s multiplier rides the same trace.
- `heavy`: `ABCPlayerController_HeavyShoot` is its own PlayerController
  class, so the cooldown is a **field** on it (a stable data address, better
  than a code branch). Find its constructor/`PostBeginPlay` + cooldown
  decrement.
- `burst`: the gauge is a per-frame component field (updated from damage
  dealt); cheapest route is the same tick trace as `heavy`.
- `skip_intro`: reachable **code-side** via the Bink natives
  (`PlayMovie`/`StopMovie`/`IsMoviePlaying`/`IsMovieFinish`/`SetInput`).
  Notably there are **zero** `.bik`/`intro`/`logo` strings in the EBOOT, so
  the intro is Kismet/sequence-driven, not a name check — there is no movie
  name to patch. The cheat is likely forcing a skip flag, not touching
  playback.
- `extras`: probably **not in the module**. No extras/gallery/artwork
  strings; the only unlock surface is achievements, which reads like
  save-profile data. Tell the user this is a profile edit, not a patch,
  rather than ship a guess — unless the unlock check turns out to live in the
  module.
- The **SPU-side angle is dropped**: the disc is a single PPU module with no
  `.sprx`, so SPU code here is generated from the PPU image. There is no
  separate SPU image to sweep; the values are either PPU code or runtime
  objects.

Per-cheat rule (updated): patch **data** where it lives in `.rodata`
(cheat_60fps's two lines — proven by the 60fps title read). Where a value
lives in a runtime object or save-profile data, a data patch may not exist —
then a **code-branch patch** is acceptable in the runtime engine (Phase 1
proved the `.text` no-op at `0x8a9458` applies cleanly), with the D-line bake
caveat. Extras stays out of the patch engine entirely (profile layer).
