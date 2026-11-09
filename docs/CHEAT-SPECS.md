# Cheat spec sheet — Asura's Wrath (BLUS30721)

Single PPU module (0 .sprx on disc) → all game logic lives in EBOOT.BIN
(patch container key `PPU-83096111daff850cc92b637aec1780c4079e1c58`, live from RPCS3.log).
Addresses are **TBD** — the current patch.yml addresses are fabricated (root cause R4).
Candidates come from `re/candidates.csv` (T-004) + disasm context (T-002).

Constant encodings (PPU is big-endian): 30.0f = `0x42F00000`, 60.0f = `0x42C00000`,
1/30 s float ≈ `0x3D2AAAAB`, 1/60 s float ≈ `0x3D2AAAAB/2 = 0x3E2AAAAB` (verify each).

| Cheat (settings.json key) | Hypothesis | Type | Address | Old → New | In-game verify | State |
|---|---|---|---|---|---|---|
| cheat_60fps | frame-cap float 30.0 → 60.0 in .rodata | be32/bef32 | TBD | 0x42F00000 → 0x42C00000 | in-game fps counter / window-title FPS | TBD |
| cheat_skip_intro | intro-skip flag / movie branch | be32 | TBD | ? | skips BIK intro | TBD |
| cheat_one_shot | damage multiplier / one-hit threshold | be32 | TBD | ? | enemies die in one hit | TBD |
| cheat_heavy (+ _cooldown off) | heavy-attack damage/cooldown constant | be32 | TBD | ? | heavy blow kills faster | TBD |
| cheat_burst (+ infinite_burst) | burst gauge cap/refill rate | be32 | TBD | ? | gauge stays full / refills | TBD |
| cheat_god | invincibility flag | be32 | TBD | ? | damage taken = 0 | TBD |
| cheat_extras / all_extras | extras/cutscene gates | be32 | TBD | ? | extra content available | TBD |

Per-cheat rule: patch **data**, not code — data survives the ppumod precompile
(verify empirically at Phase 1 probe; if constant-folded, bake the value into
EBOOT and rerun `--ppumod-build` instead — see NATIVE-PLAN §2/§8, D-line "bake").

Status column values: `candidate` → `patched` (runtime patch.yml entry) →
`baked` (value in EBOOT + ppumod rebuilt) → `verified` (in-game evidence in qa/).
