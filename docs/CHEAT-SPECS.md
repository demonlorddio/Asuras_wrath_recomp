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
| cheat_60fps | frame-cap float 30.0 → 60.0 in .rodata | be32/bef32 | `0x19afbac` (alt: `0x19cbe10`, `0x19cbe68`, `0x19a8384`) | 0x41F00000 → 0x42700000 | in-game fps counter / window-title FPS | candidate |
| cheat_skip_intro | intro-skip flag / movie branch | be32 | TBD | ? | skips BIK intro | TBD |
| cheat_one_shot | damage multiplier / one-hit threshold | be32 | TBD | ? | enemies die in one hit | TBD |
| cheat_heavy (+ _cooldown off) | heavy-attack damage/cooldown constant | be32 | TBD | ? | heavy blow kills faster | TBD |
| cheat_burst (+ infinite_burst) | burst gauge cap/refill rate | be32 | TBD | ? | gauge stays full / refills | TBD |
| cheat_god | invincibility flag | be32 | TBD | ? | damage taken = 0 | TBD |
| cheat_extras / all_extras | extras/cutscene gates | be32 | TBD | ? | extra content available | TBD |

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
