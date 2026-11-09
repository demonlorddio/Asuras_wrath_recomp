# Asura's Wrath "Native Edition" — Plan & Steps

Date: 2026-11-09 · Status: decision-ready, awaiting GO/NO-GO per phase.

## 0. TL;DR (read this first)

1. **Your build is already 80% of "our own native build".** The fork boots the game from a
   pre-compiled PPU payload (`rom_data/BLUS30721.ppumod`, 59 MB, 39,254 native x86-64
   functions, pinned to your CPU raptorlake / LLVM 23.1.4 / v9-kusa). The game code is *not*
   JIT-compiled per boot — it is hydrated from precompiled objects. That is what makes it
   feel "native". Deep-dive (2026-11-09) adds: the whole game is **one PPU module**
   (0 `.sprx` on disc) and its code is **already native x86-64** (225 LLVM objects,
   39,254 functions) — so "our own build" is host-glue work, not a CPU compiler (§8).
2. **The cheats don't work because of three stacked bugs, all verified from source + logs**
   (evidence below). None of them are "native vs emulator" — they're plumbing:
   - `patch.yml` is in the **wrong schema** — the patch engine rejects the whole file
     (`PAT: Error: No 'Version' entry found … patch.yml`, RPCS3.log).
   - There is **no `patch_config.yml`** — without it every patch is `Enabled: false` by
     default (`bin_patch.cpp` line 370-373).
   - The patch container key must be the **executable hash** `PPU-83096111daff850cc92b637aec1780c4079e1c58`
     (SHA1 of the EBOOT LOAD segments; see log), not `All`/serial.
   - **The addresses themselves are fabricated** placeholders — even with perfect plumbing
     they write to the wrong memory. Real addresses need research + RE (Phase 2).
3. **The launcher writes a fake `Patch:` section into `config.yml`** — RPCS3 has no such
   config section; it is dead YAML. The real enable-file is `~/.config/rpcs3/patch_config.yml`.
4. **A from-scratch static PPU→x86 translator (true "replace RPCS3") is a 12–24 month moonshot**
   and not what you actually want. What *is* achievable and gives you "perfect control":
   **Option A** — keep the forked runtime, but own every control surface: our patch files,
   our settings writer, our launcher, and (kicker) **baking cheats into the ppumod payload
   itself via our existing rebuild pipeline** — so the modifications live inside *your* native
   build, not in emulator patching.

### Decision points
- **Phase 1+2 (cheat plumbing + real addresses): GO?** → yes/no
- **Option A vs B vs D below: which?** (recommend A now; D as parallel upside)
- **Phase 3 cosmetic shell: GO?**

---

## 1. Root causes — evidence table

| # | Complaint | Root cause | Evidence | Fix | Effort |
|---|-----------|------------|----------|-----|--------|
| R1 | Cheats do nothing | `patch.yml` wrong schema (list-of-blocks, no `Version:` key) | RPCS3.log: `PAT: Error: No 'Version' entry found. Patch engine version = 1.2 (file: …/patches/patch.yml)` → file rejected wholesale; `bin_patch.cpp:200-217` requires `Version: "1.2"` | Rewrite in v1.2 schema (§4) | 1 h |
| R2 | Cheats do nothing | No `patch_config.yml` → `enabled` defaults false | `bin_patch.cpp:191-196,370-373,1537-1540`: enable state comes from `load_config()` (i.e. `~/.config/rpcs3/patch_config.yml`); absent ⇒ `patch_config_values{}` = disabled | Launcher writes `patch_config.yml` with `Enabled: true` | 1 h |
| R3 | Cheats do nothing | Wrong container key | `PPUModule.cpp:2457-2477`: apply uses `hash` = `PPU-` + SHA1 over each LOAD segment (`p_vaddr`, `p_memsz`, bytes), and alt key `TITLEID-hash`. Log shows the live key: `PPU-83096111daff850cc92b637aec1780c4079e1c58` | Use that key as the YAML top-level container | trivial |
| R4 | Cheats do nothing | Addresses are fabricated | current `patch.yml` blocks (`0x0012A3A4` etc.) have no provenance | Real addresses via research + RE (Phase 2) | 1–3 d |
| R5 | Overlay still on / 30 fps | Launcher wrote to `config.yml` `Patch:` (ignored) + old `update_yml` couldn't reach nested keys | `config.yml:290-296` (dead section); now `Video/Performance Overlay/Enabled: false` (line 239) and `Video/Frame limit: Off` (line 221) are correctly present after last fix | Verify in-game; launcher no longer needs the fake section | done, verify |
| R6 | "Graphics enhance doesn't work" | Values ARE applied (`Resolution Scale: 150`, `Output Scaling Mode: FSR`, `Anisotropic Filter Override: 16`, `Vblank Rate: 120` in config.yml) but FSR-upscaling a native-720p game looks close to the original | `config.yml:188-261` | A/B test on screen; try MSAA/res-scale 200; this is perception, not wiring | verify |
| R7 | "Can't tell native vs emulator" | It *is* RPCS3-derived — there is no PS3 CPU binary running; PPU code runs as precompiled x86-64. The honest markers are boot-time ones | `M4-COMPLETE.md`, ppumod manifest pin, `ppu_progs`/`spu_progs` cache dirs empty by design (hydration) | Explain + give you the verifiable markers (§5) | done |

---

## 2. Options for "replace the rpcs3 fork / our own build"

| Option | What it is | Control gained | Effort | Risk | Verdict |
|--------|-----------|----------------|--------|------|---------|
| **A. Owned shell over forked runtime** | Keep the fork as the engine; we own launcher, patch files, settings writer, and rebuild ppumod with our modifications baked in | 100% of settings/cheats/distribution control | 2–5 days | Low (proven pipeline) | **Recommended** |
| **B. Headless runtime (fork as a library)** | Link RPCS3 core into our process, drive GPU/CPU ourselves, custom input layer | Total, incl. GUI independence | 1–3 months | High (Qt/GUI entanglement, no user-visible gain over A) | Optional later |
| **C. Full static PPU→x86 translator** | From-scratch native recompile, no RPCS3 at all | Total | 12–24 months, likely infeasible (PS3 PPU = 64-bus, SPUs, CSM, atomics) | Extreme | **No** (superseded by D) |
| **D. Three-agent C-lite** | PPU code is already native (225 LLVM objects); build the host glue: linker bootstrap, ~150 VSH system-lib stubs, SPU runtime, GPU bridge, main-loop shim; RPCS3 kept only as golden reference (§8) | Total, incl. a truly-ours runtime | 1–2 mo wall-clock with 3 AIs 24/7 | Medium — PPU↔SPU sync is the hard 20% | **Optional parallel bet, gated on A working** |

Why A already delivers your stated goal ("control our stuff perfectly"):
- Every cheat becomes *our* file (patch.yml + patch_config.yml templates in the launcher).
- Cheats can be **baked into the ppumod payload**: modify the EBOOT bytes → `rebuild.sh` →
  new ppumod → the modification is *inside your native build*, not an emulator layer.
- Settings are 1:1 ours (`config.yml` writer already fixed to reach nested keys).

---

## 3. Phases & steps

### Phase 1 — Make the patch pipeline real (prerequisite; ~half a day)
1. **Prepare the RE target**: `USRDIR/EBOOT.BIN` (10,629,688 B, magic `SCE\0`) is the
   **raw PPU program form, single PPU module** (0 `.sprx` on disc) with plaintext
   PPC32 code from 0x400000. Extract the LOAD segments into an isolated RE dir
   (untrusted-data rules: own empty dir, scripts elsewhere, run python `-I`).
   Disassemble with the fork's PPU disassembler / `--ppumod-verify` dumps — host has
   no PPC binutils, but the exact LLVM 23.1.4 host toolchain (clang-23, llvm-as,
   llvm-link, opt) matching the `v9-kusa` codegen tag is already installed.
2. **Verify the patch key**: recompute SHA1 over each LOAD segment
   (`p_vaddr`, `p_memsz`, segment bytes` → PPUModule.cpp:2417-2419`) and confirm it
   matches `PPU-83096111daff850cc92b637aec1780c4079e1c58` from the log.
3. **Write the correct `~/.config/rpcs3/patches/patch.yml`** (v1.2 schema, §4) with one
   harmless probe patch (be32 NOP into a known .rodata byte) → boot → grep log for
   `PAT: Applied patch` / `ppu_loader` apply lines. **This proves the plumbing end-to-end
   with zero game risk.**
4. **Write `~/.config/rpcs3/patch_config.yml`** (template §4) enabling the probe.
5. **Launcher surgery** in `asuraswrath`:
   - replace `write_patches()` → emit both files in v1.2 schema, keyed by the PPU-hash
     (read from log or recomputed; keep a `patches_state.json`);
   - toggle cheat = rewrite `patch_config.yml` entry (`Enabled: true`/delete);
   - **stop writing the fake `Patch:` section into `config.yml`**;
   - keep the already-fixed nested `update_yml` for real settings.
6. **Verification checklist**:
   - [ ] log shows no `PAT: Error` for our files
   - [ ] probe patch reports applied
   - [ ] disabling a patch in launcher removes it from `patch_config.yml` and boot log
   - [ ] old `Patch:` section gone from config.yml

### Phase 2 — Real cheat addresses (1–3 days)
1. **Web research (gateway-gated, queue in §6)**: hunt community patches for BLUS30721
   (RPCS3 patch hub / rpcs3.sc patch lists), and finish the SpartanPort-style survey
   (how modern ports wire settings/cheats — most are RPCS3-runtimes + patch files +
   config files, i.e. exactly Option A).
2. **RE constant sweep** on the extracted EBOOT LOAD segments (single PPU module;
   VSH system libraries are not patch targets — the game's logic all lives in EBOOT):
   - 60 fps: search .rodata float `30.0` = `00 00 F0 42` (be32) near timing code;
     candidate target `60.0` = `00 00 C0 42`;
   - burst gauge / heavy-blow cooldown / god mode: look for threshold constants,
     timers, and flag bytes; verify each candidate with a single in-game test patch.
   - Cross-check with the PPU disassembly (`PPUAnalyser` output / `--ppumod-verify`
     dumps) so we patch *data*, not code (data survives the precompile; see risk 2.3).
   - Note from the deep-dive: resources are a known cooked layout (`.XXX`/`.UPK`
     COOKEDPS3 + Bink `.BIK`, `.TFC` texture packs) — engine-level knowledge beats
     blind constant hunting for timing/gauge semantics.
3. **⚠ Key risk test — constant folding**: ppumod mode runs precompiled native objects.
   A .rodata be32 patch only works if the native code *loads the value from memory*
   rather than having constant-propagated it into the native object. Test: apply one
   proven data patch, boot, observe effect. If folded:
   - **Fix = bake it**: patch the EBOOT.PPUELF bytes on disk → rerun `rebuild.sh`
     (`--ppumod-build`) → new ppumod with the cheat compiled in. This is the strongest
     "our own build" outcome: the mod lives in your native payload, not in an emulator.
   - Note: PPU is a load-store ISA, so value constants normally live in .rodata and are
     loaded — folding risk is real but low for the classic 30→60 fps style patches.
4. **Cheat spec sheet** (per cheat): `name, type(be32/bef32/be64), address, old→new,
   verify-in-game method, baked-into-ppumod or runtime-patched`.

### Phase 3 — "Perfect control" shell (after cheats work; ~1–2 days)
1. Launcher owns: settings writer (done), patch manager (Phase 1), and optionally
   a SpartanPort-style visual menu (cosmetic; defer if not wanted).
2. Ship-ready layout: `rom_data/` (ppumod + manifest + our patched-payload recipe),
   `patches/` (v1.2 files), `settings.json`, launcher binary.
3. Legal note (per RECOMPSTORE.md): the *recipe + tooling* is distributable; a patched
   ppumod payload is a GPL-3 derivative of game code — ship source/recipe, not binary.

### Phase 4 — Tooling & skills (gateway-gated; queued in §6)
1. Install the 5 requested skill/plugin packs.
2. Re-spawn the two dead research agents (PS3-port mechanisms; disc deep-dive) —
   the disc half is already done locally (see §1 evidence); only the web half remains.

### Phase 5 — QA matrix
1. 720p/1080p/1440p × FSR/MSAA/none, overlay on/off, each cheat on/off (7 × combos).
2. Evidence: screenshots + log greps per combo; keep in `qa/` folder.

---

## 4. Exact file templates (v1.2 patch engine, verified against `bin_patch.cpp`)

### `~/.config/rpcs3/patches/patch.yml`
```yaml
Version: "1.2"
PPU-83096111daff850cc92b637aec1780c4079e1c58:
  60 FPS Unlock:
    Games:
      "Asura's Wrath":
        BLUS30721:
          - All
    Author: "dio"
    Notes: "Replaces 30.0f frame cap with 60.0f in EBOOT .rodata (ADDR TBD via RE)"
    Patch:
      - [ be32, 0xREPLACE_WITH_REAL_ADDR, 0x42C00000 ]
```
Schema rules the parser enforces (`bin_patch.cpp:200-460`):
- top-level requires `Version: "1.2"` (else the whole file is rejected);
- top-level keys = container "hash" — for the main executable that's `PPU-<sha1>`
  (PPUModule.cpp:2457-2477);
- `Games:` is a nested map `title → serial → [app versions]`;
  if title ≠ `All`, serial must be the real 9-char serial (never `All`);
  if title = `All`, serial must be `All`;
- app versions: `All` or `NN.NN` — use `All`.

### `~/.config/rpcs3/patch_config.yml` (the enable file)
```yaml
PPU-83096111daff850cc92b637aec1780c4079e1c58:
  60 FPS Unlock:
    "Asura's Wrath":
      BLUS30721:
        All:
          Enabled: true
```
Toggling a cheat = set `Enabled: false` or drop the entry (`load_config`
defaults missing entries to disabled).

### Launcher changes
- `write_patches()` → emit both files above, one block per enabled cheat, keyed by
  `PPU_HASH` (recompute when EBOOT changes; else read the last value from RPCS3.log).
- Remove the `Patch:` block from `save_settings()`'s `update_yml` calls.

---

## 5. "Native vs emulator" — verifiable markers (answer to R7)
- **Native-feel markers (true today)**: zero in-session PPU compilation
  (`~/.cache/rpcs3/` `ppu_progs`/`spu_progs` stay empty; hydration is from `rom_data/`),
  instant boot after first hydration, `Window Title Format` in config, no RPCS3 progress
  dialogs when `show PPU compilation hint` is satisfied.
- **Emulator markers (inevitable)**: it is an RPCS3-derivative process; logs,
  `dev_hdd0/dev_bdvd` layout, RPCN section in config. There is no way to make it
  indistinguishable — and Option A keeps it honest while giving total control.

---

## 6. Gateway-gated queue (run the moment free-stack/127.0.0.1:20128 recovers)
```
npx skills add jeffallan/claude-skills
npx skills add trailofbits/skills
npx skills add mohitmishra786/low-level-dev-skills
/plugin marketplace add EncidXVII/claude-reverse-engineering-skill
/plugin install reverse-engineering@reverse-engineering-skill
```
+ WebFetch: `github.com/FelipePrado0/SpartanPort` (arch + settings/cheat wiring),
RPCS3 patch-hub pages for BLUS30721/GoW-III real patch examples.

## 7. Risks
1. **PPU-hash drift** — if EBOOT or ppumod is rebuilt, the `PPU-…` key changes;
   Phase 1.2's recompute keeps the launcher correct.
2. **Constant folding in precompiled objects** — mitigated by the bake-into-ppumod
   strategy (Phase 2.3).
3. **Legal** — patched native payload = derivative work (RECOMPSTORE.md rules:
   distribute recipe + source, not compiled game code).
4. **Gateway flakiness** — web research & skill installs blocked until it recovers;
   everything else in this plan is local and unblocked.

## 8. Option D — three-agent C-lite (decision artifact, pending GO)

Deep-dive verdict: **the PPU program is already native x86-64** — the hard CPU-compile
work is done; what remains is host glue. Work items (from the deep-dive report):

| # | Item | Est. | Suggested owner |
|---|------|------|-----------------|
| D1 | Bootstrap/linker: `llvm-link` the 225 objects into one x86-64 ELF; resolve PPU import symbols to native targets | 1–2 wks | Freebuff |
| D2 | Native PS3 system-lib layer — ~150 VSH `ppu-*.sprx` syscalls (sys_ppu_thread, sys_spu, sys_memory, sys_rsx, sys_fs, sys_hid, …) — **the biggest gap** | 6–10 wks | Omnirush swarm |
| D3 | SPU runtime: MegaSAFE + safe pools, MFC/DMA, **PPU↔SPU sync (CSM, reservations, atomics) — the hard 20%** | 4–6 wks | Omnirush (strongest model) |
| D4 | GPU bridge: GS/GCM → Vulkan, lift the fork's RSX proxy instead of reinventing | 3–4 wks | Freebuff |
| D5 | PPU main-loop shim: `ppu_load_module` + PPU start on a host thread; boot the game entry point | 1 wk | Me |

**Golden rule:** everything diffs against the fork's interpreter + recompiler — the
39,254-function corpus, zero register-diff at each checkpoint.

**Checkpoints (with kill criteria):**
- C1 (~wk 3): linked ELF reaches the PPU entry, syscalls routed to the native layer
- C2 (~wk 6): PPU parity diff-clean on the corpus — **KILL D here if not clean**,
  keep A (A already delivers the value)
- C3 (~wk 10): SPU + GPU lifted, game playable end-to-end
- C4 (~wk 12): full playthrough diff-clean; RPCS3 removed from the runtime path

**Capacity mapping (per user, 2026-11-09):** Omnirush = most usage + GPT 6 Astra →
D2/D3 + buildathon fuzz workers; me (Agnes via omniroute; switch to the claude-code
combo during gate weeks — free-stack has been flapping) = harness design + all merge
gates; Freebuff (free models, all-day throughput) = D1/D4 volume work.

**Wall-clock: ~1–2 months with all three 24/7.** Prerequisite: Phases 1–3 done and
Option A running, so cheats/settings work regardless of D's outcome.
