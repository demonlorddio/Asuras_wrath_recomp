# Asura's Wrath (BLUS30721) Recompile Payload — Deep Analysis Report

Source: subagent deep-dive (task a0d097d39f7856465), 2026-11-09. Read-only inspection;
nothing modified, emulator/game not launched. All paths absolute.

## 1. PS3_GAME / USRDIR tree
**Disc payload root:** /home/dio/Games/AsurasWrathRecomp-linux-x86_64/disc_extracted/
Total USRDIR ≈ 6.5 GB, 2317 files.

**EBOOT.BIN** — .../PS3_GAME/USRDIR/EBOOT.BIN
- 10,629,688 B (~10.6 MB). Header ASCII `SCE\0` (53 43 45 00), **not** a 0x8B
  encrypted SELF — i.e. rpcs3's raw/decrypted PPU program form; PPU code in the
  extracted payload is plaintext PPC32 (instruction-like bytes at 0x400000).
- It is the **single PPU module**. **0 `.sprx` files** on the disc.

**Resource packs by extension (totals):**
- .XXX 2198 files / 3494.5 MB (Unreal cooked resources)
- .BIK 68 / 2182.7 MB (Bink movies)
- .TFC 3 / 1214.7 MB (TEXTURES.TFC 753 MB, CHARTEXTURES.TFC 270 MB, LIGHTING.TFC 135 MB)
- .UPK 1 / 25.9 MB (Unreal package)
- .BIN 12 / 21.8 MB; .PDB 2 / 2.3 MB; other: .TXT×8, .DLL×2, .PNG×1, .BAT×1,
  .UNCOMPRESSED_SIZE×20, .PROPERTIES×1
- Layout: BCGAME/ (COOKEDPS3, MOVIES), BINARIES/ (PS3/BINK/*.BIN, PS3TOOLS*.DLL/PDB,
  FORMATHDD.BAT, UNREALFRONTEND_TMPEXEC.TXT). Unreal + Bink title.

## 2. PARAM.SFO
.../PS3_GAME/PARAM.SFO (1040 B): TITLE=`ASURA'S WRATH`, TITLE_ID=`BLUS30721`,
VERSION=`01.02`, APP_VER=`01.00`, PS3_SYSTEM_VER=`03.7300`, CATEGORY=`Library programs`.
**No NpTitleId.**

## 3. PS3_UPDATE
.../PS3_UPDATE/PS3UPDAT.PUP = 268,435,456 B (256 MB), magic `SCEUF` (PUP container).
Last nonzero byte at 0xB9849AF (~185.6 MB real content, zero-padded to 256 MB).

## 4. rom_data
- .../rom_data/BLUS30721.ppumod = 59,456,372 B. Magic `PPUM` + module-id +
  `v9-kusa` + `23.1.4` + `raptorlake`. Holds **225 gzip LLVM x86-64 `.obj` files**
  for EBOOT.BIN.
- .../rom_data/BLUS30721.manifest.json = 585,087 B. pin = { ppu_module_id
  `3ad77062fa1a5fc9b724e55d9c1749a4b0aee72cbe02d9ca955ee188221a1e54`, title BLUS30721,
  disc_sha256 `c6fd7f6ec25b5dadb0279e4fdec0e47b33a1baa0f1ae1911f48ea9ff626926eb`,
  codegen_tag `v9-kusa`, llvm `23.1.4`, target `raptorlake`, generator_ver 1 }.
  statistics = { total_entries 227, obj_files 225, function_count **39,254**,
  payload_bytes 59,422,148 }. Single PPU module; build state = 225 compiled objects.

## 5. engine/rpcs3
.../engine/rpcs3 = 71,703,968 B. **Custom "ps3-recomp" RPCS3 fork**, version
`RPCS3 0.0.43-4-7c735797 Alpha`. Links libLLVM.so.23.1, SDL3, Qt6, vulkan, GL/GLEW,
absl. Source: /home/dio/Projects/ps3-recomp/rpcs3/. Custom flags `--ppumod-build`,
`--ppumod`, `--ppumod-verify`, `--ppumod-manifest`. Not a stock release.

## 6. RPCS3 caches (~/.cache/rpcs3 = 107 MB)
- cache/BLUS30721 = 66 MB → ppu-U4d6KieMMsKi2HjjqkGPE11XS3m2-EBOOT.BIN/ holds 228
  entries: 225 × v9-kusa-…-raptorlake.obj.gz (each decompresses to a native ELF
  64-bit x86-64 relocatable), plus spu-mega-v1-tane.dat (1.42 MB),
  spu-safe-v1-tane.dat (1.70 MB), shaders_cache/.
- cache/vsh = 4.9 MB — ~150 ppu-*.sprx system-lib dirs (libvoice_internal, sys_audio,
  libdivx311dec, …).
- cache/BCES00510 = 11 MB (another game's EBOOT); ppu_progs/spu_progs/shaderlog = 0.
- **The "zero-precompile" claim is substantiated:** the 225 objects are already
  materialized in the cache and hydrated directly.

## 7. Patch / config state (as found)
- ~/.config/rpcs3/config.yml `Patch:` block "enables" 6 cheats — **dead YAML**, RPCS3
  does not read that section (root cause R1/R2 in NATIVE-PLAN.md §1).
- ~/.config/rpcs3/patches/patch.yml (1380 B) defines 6 synthetic **be32** patches
  (e.g. 60fps [be32, 0x0012A3A4, 0x3C0041F0], god_mode [be32, 0x005E3C10, 0x48000004])
  — wrong schema (rejected: "No 'Version' entry found") **and fabricated addresses**.

## 8. Available RE tooling
Present: objdump (binutils x86-64, **no PPC disassembler**), **llvm-objdump =
LLVM 23.1.4 (exact codegen-tag match)**, readelf, gdb, python3, clang-23, llvm-as,
llvm-link, opt.
Missing: unself, make_fself, radare2/rizin, ghidra, qemu, ppc-objdump, binwalk.
**Key point:** the full host LLVM 23.1.4 toolchain is installed — the exact toolchain
that generated the ppumod objects; a standalone build must link against it.

## 9. Launcher wiring
asuraswrath (24,401 B, Python/tkinter): RPCS3_BIN = env → bundled engine/rpcs3 →
build/bin/rpcs3. configure_engine() sets Core/PPU Modules Mode = Prefer +
PPU Modules Dir = rom_data/. write_patches() writes the be32 cheats to patch.yml +
the (dead) Patch: section in config.yml. rebuild() runs
`rpcs3 --ppumod-build <module> --ppumod-title <title> <game_path>`.
launch() runs `rpcs3 --no-gui [--fullscreen] <game_path>`.
recomp.cfg: title=BLUS30721, game_path=…/disc_extracted, disc_pin=…iso,
module=…/rom_data/BLUS30721.ppumod.
settings.json: all cheats true; FSR; 150% res scale; 120 Hz vblank; 16× aniso; 720p.

## Assessment: what already exists vs. what must be built
**Already exists (reusable as-is):**
1. EBOOT.BIN's PPU program **already compiled to 225 native x86-64 LLVM objects**
   (39,254 functions) — in rom_data/BLUS30721.ppumod and
   ~/.cache/rpcs3/cache/BLUS30721/ppu-…-EBOOT.BIN/.
2. Host **LLVM 23.1.4** toolchain (clang-23, llvm-as, llvm-link, opt) matching
   the codegen tag.
3. All decrypted game content (~6.5 GB USRDIR).
4. The 6 be32 cheat definitions and SPU thread data (spu-mega / spu-safe .dat).

**Must be built for a standalone/custom native runtime (Option D):**
1. **Bootstrap/linker:** llvm-link the 225 objects into one x86-64 executable;
   resolve PPU import symbols to native targets.
2. **Native PS3 system-library layer** — biggest gap. The game links against the
   VSH/Syscall set (~150 ppu-*.sprx under cache/vsh: sys_ppu_thread, sys_prx,
   sys_spu, sys_memory, sys_crypto, sys_rsax, sys_hid, sys_config, sys_fs, sys_net, …).
3. **SPU/Cell subcore runtime** (MegaSAFE / safe pools present) — native SPU support
   or a bridge.
4. **GPU path** — RPCS3's RSX proxy (Vulkan) renders; re-implement or bridge
   GS/GCM → host GPU.
5. **PPU main-loop shim** — ppu_load_module + PPU start, invoke the game's EBOOT
   entry point on a host thread.

**Bottom line:** the PPU code itself is already native x86-64; remaining work is
entirely host glue — linking the objects, native implementations of the PS3 system
libraries, and a runtime bootstrap plus GPU/SPU bridges.

Constraint compliance: read-only throughout; emulator and game not launched;
no files written.
