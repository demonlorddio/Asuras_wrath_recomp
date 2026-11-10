# E5 skybox artifact — red speckle + black checkerboard (investigation)

Reported in MSG-0019 by agnes, from the E5 play session (2026-11-10, ~10:40):
"red-speckled + black-checkerboard skybox/particle artifact", RSX log clean
(no PVR/decode errors), FIOS TFC opens for TEXTURES.TFC + CHARTEXTURES.TFC
succeeded, only CELL_ENOENT probes for the INSTALL dir and `BCGAME/PS3TOC.TXT`.

This pass is repo-local forensics only. Nobody has booted the scene for it yet.

## What this pass could NOT check (limitation, read this first)

- **No gameplay log survives.** `~/.cache/rpcs3/RPCS3.log` is a boot-only run:
  it ends at `0:00:11.69`, five seconds after renderer init. The rotated
  `RPCS3.log.gz` is mode `000` and unreadable, `TTY.log` is empty, and
  `~/.config/rpcs3/captures/` is empty — there is no screenshot and no RSX
  trace from the E5 session to look at.
- So nothing below is "the artifact is caused by X". The config/data facts are
  verified; the hypotheses are ranked, not confirmed.

## Verified on disk this pass

1. **The missing-file probes from MSG-0019 do not reproduce, and the files exist.**
   `USRDIR/BCGAME/PS3TOC.TXT` is present (139,729 B, 2,309 lines) along with five
   localized variants (`_DEU/_ESN/_FRA/_ITA/_JPN`). The surviving log contains no
   ENOENT at all — its only "not found" line is RPCS3's own
   `Jump table not found! 0x1be007c-0x1bf3b68` (normal for a stripped EBOOT).
   `LIGHTING.TFC` (141,909,738 B) also exists next to
   `TEXTURES.TFC` (789,478,279 B) and `CHARTEXTURES.TFC` (283,349,133 B), and the
   log shows `sys_fs_stat` on all three. => the "streaming files are missing"
   branch is not supported by anything on disk.

2. **The TFCs are zlib-compressed-chunk containers, not raw DXT.** Header of all
   three: tag `0x9E2A83C1`, version `1`, then a repeated `(count, size)` pair
   (TEXTURES `6101 / 8192`, CHARTEXTURES `100 / 256`, LIGHTING `2251 / 4096`),
   and the payload at `0x18` starts `78 9C` (zlib). The exact meaning of the
   second number is not settled here (chunk size, or a block count); what
   matters is that the payload is zlib-compressed, i.e. it is decoded at load. Consequence for the artifact:
   texture bytes reach the RSX **through a decompress + swizzle step**, so a
   decode fault produces garbage tiles (speckle) and a failed decode produces the
   engine's fallback (checkerboard) — the two symptoms reported are exactly the
   two failure modes of that step.

3. **Live renderer config at the time (`~/.config/rpcs3/config.yml`).**
   Vulkan on RTX 3050 Laptop, `Resolution Scale: 150`, `Anisotropic Filter
   Override: 16`, `Handle RSX Memory Tiling: false`, `Write Color Buffers: true`,
   `Read Color Buffers: true`, `Write/Read Depth Buffer: false`,
   `MSAA: Auto`, `Shader Mode: Async Recompiler with Shader Interpreter`,
   `Vblank Rate: 120`, `Frame limit: Off`, `Multithreaded RSX: false`,
   and — new information for this project — **`PPU Modules Mode: Prefer`**.
   SPU side: `SPU Decoder: Recompiler (ASMJIT)`, `Accurate SPU DMA: false`,
   `SPU XFloat Accuracy: Approximate`, `SPU loop detection: false`.

4. **Two renderer-side log signals, both unclassified.**
   - `RSX TODO: Vertex textures are currently not implemented for the shader
     interpreter.` ×2 at 1.87 s / 2.18 s. Only matters if a shader samples a
     vertex texture; UE3 does not normally, so this is probably noise — but it is
     the only "unimplemented" renderer message in the whole log.
   - `SPU: Channel Loop Pattern Detected! ... (read_pc=0x15c4 ...)` at 9.98 s.
     RPCS3's own warning, fires from a spin-wait pattern. Could be benign or could
     mark an SPU sync inaccuracy; it has a `SPU Verification` toggle that would
     settle it (`SPU Verification: true` is already set, and it did not fire).

## Hypothesis ranking, cheapest test first

The artifact is in one of four layers, and each layer has a one-toggle or
one-setting discriminator. Do them in this order — each one is a single Play and
each one eliminates half the space.

**H1 — our own patches (cheapest, and the least comfortable).**
The E5 session ran with the T-004 float (`0x19afbac` = 60.0f) live, and the
global sleep scale patch (`0x8a9438` = 500000.0) halves **every** sleep in the
game, not just frame pacing — MSG-0023 flagged exactly this ("anything paced by a
different constant now runs 2x fast"). UE3 texture streaming is deadline/budget
driven; a halved virtual-time budget is a plausible way to get placeholder
textures. Test: **all cheats off**, same E5 scene. Artifact gone => it is our
patch, and the fix is to stop scaling the streaming-side sleeps (patch that call
site, not the rate).

**H2 — Resolution Scale 150 with `Handle RSX Memory Tiling: false`.**
1.5x scaling is the launcher's default (`settings.json`), not an upstream
default. PS3 UE3 render targets are tiled; scaling + tiling off is the classic
combination for checkerboard/banding artifacts on render-target-sampled content
(the skybox is often a render from the reflection/atmosphere pass). Test: set
**Resolution Scale 100**, everything else identical. Cheap, reversible, and it
also tells us whether the 150 default should ship at all.

**H3 — ppumod codegen (the game's own decompress/swizzle code).**
`PPU Modules Mode: Prefer` means the game's PPU code is the precompiled LLVM
payload; the TFC decompress + swizzle runs *there*. A miscompile in a byte-swap
or saturated-pack path would corrupt textures while leaving logic and framerate
perfect. Test: `PPU Modules Mode: Off` (falls back to the standard RPCS3
JIT/LLVM path). Identical artifact => not our codegen. This is the single most
valuable test for this project, because it is the only one that separates "the
runtime we own" from "RPCS3 at large".

**H4 — upstream RPCS3 behaviour (the fork is not the only suspect).**
The fork carries 4 commits, all ppumod plumbing (loader, container, config key,
cmake option) — nothing touches RSX. So the renderer is effectively upstream, and
if H1–H3 all come back clean, the artifact is likely a known
RPCS3-on-UE3/PS3 issue (cubemap or DXT swizzle). Test: the same scene on a stock
RPCS3 release with the same disc; if it reproduces there too, this stops being a
recomp bug and becomes an upstream report — which is a much better use of time
than patching around it.

## Concrete next action

One toggle per Play, in the order H1 → H2 → H3, with a screenshot at the same
camera position for each. Nothing in this repo should change until one of those
four brackets the fault; a patch for a renderer artefact we cannot localise is
exactly the kind of guess R4 exists to prevent.

## Side observations recorded, not chased

- The launcher writes `Output Scaling Mode` as a quoted string; the surviving log
  shows `CFG: cfg::try_to_enum_value('FSR', 'Output Scaling Mode'): invalid enum
  or integer` twice — the known `"\"FSR\""` bug (already tracked). Effect is a
  silent fallback to Bilinear, not a checkerboard.
- `Vblank Rate: 120` with `Frame limit: Off` is a deliberate 120 Hz setup for the
  60 fps work; it is not obviously related to texture content.
- `Accurate SPU DMA: false` + `SPU XFloat Accuracy: Approximate` are upstream
  defaults, not our settings.
