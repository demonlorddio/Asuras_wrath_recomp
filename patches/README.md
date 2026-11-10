# patches/ — v1.2 patch pipeline (Phase 1)

Templates for the two files RPCS3's v1.2 patch engine reads. The launcher
(`$LAUNCHER/asuraswrath`) regenerates these under `~/.config/rpcs3/` on every
save; edit the **live** copies for quick tests, edit these templates for
repo-tracked changes.

| Live file | Engine path (bin_patch.cpp) |
|---|---|
| `~/.config/rpcs3/patches/patch.yml` | `get_patches_path()+"patch.yml"` (global) |
| `~/.config/rpcs3/patch_config.yml` | `get_patch_config_path()` (enable bookkeeping) |

## Keying

The main key is the **PPU executable hash**, not the title ID:

```
PPU-83096111daff850cc92b637aec1780c4079e1c58
```

Confirmed by 4 independent signals (live RPCS3.log value, big-endian recompute
from EBOOT.elf, base57 forward-encode of the live cache-dir key, live cache
dir mapping) — see `../re/ppu-hash.txt`. When the PPU module image changes
(e.g. a new ppumod build), the hash changes and the patch files must be
re-keyed.

## Engine contract (v1.2, source-verified)

- Top-level must contain `Version: "1.2"` scalar, else the whole file is
  rejected ("No 'Version' entry found").
- Remaining top-level keys are the main keys (Maps). `Anchors` is skipped.
- Patch line = `[ type, addr, value ]`; be32 requires a `0x`-prefixed address
  (PPU vaddr, e.g. `0x10100`).
- A 4-aligned be32 write unconditionally increments the applied counter →
  success log `PAT: Applied patch (...) (<- N)`.
- `patch_config.yml` missing ⇒ every patch defaults to `Enabled: false`
  (nothing applies). Present with `Enabled: true` ⇒ applies.
- Log success path: `PPU executable hash: PPU-83096111…58 (<- 1)`.

## Current content

Two blocks under the PPU hash key:

1. `Pipeline Probe (Phase 1)` — a guaranteed no-op: be32 self-write of
   `0x00000000` at PPU vaddr `0x10100` (seg0 + 0x100, four zero bytes inside
   the module image's phdr area). It exercises the entire load→config→apply→
   counter→log path with zero risk. Kept in Phase 2 so a first-boot log can
   separate "engine accepted the real block" from "candidate address is
   valid".
2. `60FPS Unlock` — the T-004 candidate for `cheat_60fps`:
   `[ bef32, 0x19afbac, 60.0 ]`. 30.0f→60.0f at PPU vaddr `0x19afbac` (seg1
   + 0x6FBAC), the only `.rodata` 30.0f with a proven code reader
   (`lwz 4,-1108(2)` @ 0xe0d078 → `bl 0xf31c58` → `cmpwi`). Confidence
   low–medium; if it applies but the in-game fps counter doesn't move, the cap
   is a code immediate and the cheat moves to the D-line "bake" path
   (Freebuff's proposed T-005 trace).

**Syntax gotcha (source-verified, bin_patch.cpp:808):** the float patch types
`bef32`/`lef32`/`bef64`/`lef64` read the value field as a **decimal float**
(`get_yaml_node_value<f32>`), not a hex word. Writing `[ bef32, 0x19afbac,
0x42700000 ]` fails yaml-cpp `bad conversion` and the engine skips the whole
block (`PAT: Skipping patch data entry: [ bef32, … ] … bad conversion`).
Write `60.0` (the engine encodes it big-endian on the store).

## Verify (NATIVE-PLAN Phase 1 step 6, Phase 2 extension)

1. Boot the game (launcher or `FORK_BUILD --no-gui $DISC`).
2. Grep `/home/dio/.cache/rpcs3/RPCS3.log`:
   - enabled: two `PAT: Applied patch` lines (`60FPS Unlock` +
     `Pipeline Probe`), `PPU executable hash: PPU-83096111…58 (<- 2)`, zero
     `PAT: … Error`/`Skipping` lines.
   - disabled (both `Enabled: false` in `patch_config.yml`): the hash line
     appears **without** `(<- N)`, zero `Applied patch`.
   - confirm no `Skipping patch data entry` line for the 60FPS block (that's
     the hex-value bug above).
3. Confirm the old fake `Patch:` section is gone from
   `~/.config/rpcs3/config.yml`.
