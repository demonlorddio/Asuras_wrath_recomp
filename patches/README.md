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

`Pipeline Probe (Phase 1)` — a guaranteed no-op: be32 self-write of `0x00000000`
at PPU vaddr `0x10100` (seg0 + 0x100, four zero bytes inside the module
image's phdr area). It exercises the entire load→config→apply→counter→log path
with zero risk. It exists to prove the pipeline before T-004 lands the real
60 FPS `.rodata` constant addresses.

## Verify (NATIVE-PLAN Phase 1 step 6)

1. Boot the game (launcher or `FORK_BUILD --no-gui $DISC`).
2. Grep `/home/dio/.cache/rpcs3/RPCS3.log`:
   - `PAT: Applied patch` with `(<- 1)`
   - `PPU executable hash: PPU-83096111…58 (<- 1)`
   - zero `PAT: ... Error` lines for our files
3. Disable test: set `Enabled: false` (or delete the `patch_config.yml` entry)
   and reboot → the hash line appears **without** `(<- N)`, no `Applied patch`.
4. Confirm the old fake `Patch:` section is gone from `~/.config/rpcs3/config.yml`.
