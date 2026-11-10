# Queue — 2026-11-09

## Agnes (this session) — owns `~/.config/rpcs3/*` + launcher dir, no one else touches those
- [x] Plan + root-cause evidence → docs/NATIVE-PLAN.md (in repo, synced copy)
- [x] **Phase 1** — patch pipeline: correct v1.2 `patch.yml` + `patch_config.yml`
      (probe patch first), launcher surgery, log-line verification
      (done 2026-11-09: no-op probe `be32 @ PPU vaddr 0x10100`, boot-verified
      both directions — enabled: `PAT: Applied patch … (<- 1)`; disabled:
      warning-variant hash line, 0 applied. Live files under `~/.config/rpcs3`,
      templates in `patches/`, launcher writes `patches_state.json`.)
- [x] **Phase 2** — consume `re/` outputs (T-002/004), finalize CHEAT-SPECS.md
      (wiring done 2026-11-10: T-004 merged to master @72d302b; launcher
      `CHEAT_LINES["cheat_60fps"] = [ bef32, 0x19afbac, 60.0 ]` — the value
      must be a DECIMAL float, a hex word makes the engine skip the block
      (bin_patch.cpp:808); boot-verified both directions: enabled = 2x
      `Applied patch (<- 2)`, disabled = warning-variant hash line, 0 applied.
      In-game observation 2026-11-10 (MSG-0014): with both blocks applied
      (hash line `<- 2`), FPS overlay reads 30.36 avg / frametime 17.3 ms
      while total CPU is only 15% (PPU 3.3 / SPU 6.3 / RSX 5.5) -> the cap
      is the game's own pacing, not the emulator. **Trigger condition met:
      T-005 below is claimable.**)
- [ ] **Phase 2b** — P1 diagnostic (T-005 follow-up, 2026-11-10): P1
      (be32 no-op of the `0x8a9458` sleep helper) is wired; clean in-game
      read pending. **RECORD CORRECTION (supersedes the claim inside
      `73e35eb`, no history rewrite):** the "60.00 fps" read was from a
      boot where P1 was NOT live. Root cause: the user's GUI Play press
      regenerates the live patch files from the GUI's in-memory state
      (`launch_game -> save_settings -> write_patches`), and that GUI
      (started 15:56) predated the P1 edit — so the 16:01:44 boot ran
      1-line probe no-op + 60FPS Unlock only (hash `<- 2)`); its
      framerate box av ~31.8 is the P1-off baseline (≈ the 30.36 from
      MSG-0014). The later `boot_test p1clean` "<- 2" result was likewise
      stale — its log polling was contaminated by that concurrent game
      session. Fix: P1 now lives in the launcher's `PROBE_LINES`
      (regeneration-proof: every Play press rewrites the live files from
      these in-memory lists) + a headless regen script (job tmp
      `regen_patches.py`); live files verified two-line probe @ 16:07:31.
      P1 application (expect probe `(<- 2)`, hash `<- 3)`) is still
      unconfirmed in a single-engine boot. Next: user closes the game +
      the old GUI, reopens the launcher (fresh in-memory P1 lines),
      presses Play, stays on the title screen ~1 min (P1 busy-polls
      init/IO waits — keep it short), and reports the framerate-box
      AVERAGE, not the instantaneous FPS line. Routing unchanged: av
      past 30 → sleep-shaped → P2 round (`[ bef32, 0x8a9438, 500000.0 ]`);
      unchanged → §5 trace to Freebuff. MSG-0017 posted with the
      correction. If P2 lands a stable 60, P2 replaces the refuted
      `0x19afbac` line as `cheat_60fps` in launcher + templates, and
      PROBE_LINES reverts to the single no-op.
- [ ] D merge gates C1–C4 (when Option D launches)

## Freebuff — work these IN ORDER, repo-local only (zero conflict with Agnes)
- [x] **T-002** PPU disassembly pipeline + PPUAnalyser dumps → `re/disasm/`, `re/ppuanalyser/`
      (done 2026-11-09: 39,248 functions, 262 syscall sites, PPU hash MATCH — report at the bottom of T-002.md)
- [x] **T-003** static link 225 objects → import inventory → `re/imports.txt` + `docs/D2-tasklist.md`
      (done 2026-11-09: `ld.lld -r`, 480 imports, 52 lv2 syscalls in 11 namespaces, 417 unresolved vaddrs)
- [x] **T-004** .rodata candidate sweep → `re/candidates.csv` (+ top-5 rationale in `docs/`)
      (done 2026-11-10: 4,585 hits / 124,520 refs; spec's float encodings were wrong and are
      corrected; only `cheat_60fps` has a candidate `0x19afbac`, other slots left TBD on purpose)
- [x] **T-005** frame-pacing trace (done 2026-11-10: no 33 ms sleep anywhere —
      all 70 sleeps go through `0x8a9458` with 10–1200 µs or dynamic args; the six
      code-side 1/30 words are dead pools / curve math / a startup wait, so the
      D-line-bake lead is closed; `0x160bbf0` identified as the 2^32 timebase
      scaler. Two one-word probes + a debugger recipe in
      `docs/t005-frame-pacing.md` — **P1 = no-op `0x8a9458`, one boot decides
      whether the cap is a sleep or an event wait.**)

Each T-xxx file is self-contained (inputs, outputs, acceptance). Claim = flip
`Status:` in the file to `in_progress (Freebuff)`; leave findings + a report
section at the bottom when done. Branch `T-xxx` per task.

## Omnirush — in maintenance; on return, its queue is pre-built by T-003
- [ ] D2: system-lib packages from `docs/D2-tasklist.md` (one section per library,
      with symbol counts — swarm-ready work packages)
- [ ] D3: PPU↔SPU sync (CSM, reservations, atomics) — the hard 20%, GPT-6-Astra territory
