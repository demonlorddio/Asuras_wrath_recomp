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
      AVERAGE, not the instantaneous FPS line.
      **E5 DATA POINT (16:01:44 boot = P1-OFF baseline):** user played
      Episode 5 in that session — in-game framerate box av 57.9 /
      mn 54.3 / mx 60.8, frametime av 17.3 ms, CPU total 22.0% (PPU
      4.0 / SPU 11.9 / RSX 6.2). The gameplay loop already runs ~60
      with only the T-004 `0x19afbac` float; the residual ~31 (box av
      31.8) is the title/menu loop only. So the P1/P2 branch now
      classifies the TITLE loop, not gameplay. P1 was never live in
      any boot (16:01 boot predated the PROBE_LINES edit; p1clean was
      contaminated by the concurrent session — its engine exited early,
      grep returned the stale 16:01 line). Live files carry the
      two-line probe since 16:07:31, no GUI Play since; user just
      closed everything => their NEXT Play press = first P1 live boot
      (single engine, expect `<- 2)` probe + `<- 3)` hash).
      **P1 CLEAN BOOT DONE (16:28:09):** single engine, fresh header,
      hash `<- 3)` = probe `(<- 2)` + 60FPS `(<- 1)`; no PPU
      section/skip/error complaint — the `.text` no-op write at
      0x8a9458 was accepted cleanly (first observation of the
      section check on a .text write). Pre-title read with P1 live:
      framerate box **av 205.7 / mn 4.5 / mx 1154.5**, frametime box
      av 29.7 ms / mx ~60.9. The loop FREED UP when the sleep helper
      was no-op'd, so an event-wait cap is ruled out — **the ~30
      pacing is SLEEP-SHAPED** (Freebuff's declared "av past 30 → P2"
      branch). The user-visible "freeze before the title" is a P1
      busy-poll artifact, not the game. P2 (`[ bef32, 0x0008a9438,
      500000.0 ]` + the 0x10100 canary) is now staged in
      `PROBE_LINES`; pending the user closing the P1 session, then
      headless regen + single-engine boot-verify (expect probe
      `(<- 2)`, hash `<- 3)`), then their next Play = the P2 title
      read. P2 routing: av ~60 → 0x8a9438 is the frame-budget word,
      Freebuff finds its caller in `re/t005-sleep-sites.csv` and we
      bake the fix; av ~30 → the word isn't the pacing constant, send
      the §5 trace. MSG-0019 + MSG-0020 posted.
      **P2 CONFIRMED (user title-screen read, 16:4x):** framerate box
      av 54.7 / mn 27.3 / mx 60.0, frametime av 17.3 ms, overlay
      "FPS 56.97 / PPU 3.0%" — title/boot loop now caps at 60.
      `0x8a9438` is the load-bearing frame-budget word; P2's value
      (500000.0 = halved 1e6 rate) is the title-loop 60fps fix. Two
      open questions → Freebuff (MSG-0021): (a) is 500000.0 final or
      tune it (what is the native word?); (b) does 0x8a9438 also
      govern the GAMEPLAY loop (supersedes 0x19afbac=60.0f) or is it
      title-only (final = P2 title + 0x19afbac gameplay). Until (b),
      P2 stays in PROBE_LINES (regeneration-proof); repo template
      keeps its final-target shape.
      **CHEAT-SLOT STATUS (T-006, user-priority, MSG-0021 on bus):**
      launcher now has 7 slots — `cheat_extras` ("Unlock All Extras")
      was GUI-complete (checkbox + default True + save key) but
      missing from CHEAT_LINES/CHEAT_LABELS; wired this session (empty
      slot emits no block, same as the other five). T-006 covers six:
      skip_intro, one_shot, heavy, burst, god, extras.
      candidates.csv census: the sweep covered only float constants
      (1.0/0.5/-1.0, 60/30 as int+float, 1/30 & 1/60 s, 120.0f, a few
      doubles) — god/skip/one-shot values appear in no swept pattern,
      consistent with T-004 ("runtime/heap state machines, not
      .rodata"). **SPU-side angle DROPPED (T-006):** no .sprx on the
      disc means no separate SPU image to sweep — SPU code here is
      generated from the PPU image, so the remaining angles are
      function-prologue / code-branch (fine in the runtime engine,
      D-line bake caveat applies).
      **P2 FINALIZED (T-006 §0 / MSG-0023 @ c64b59d, 2026-11-10):**
      no tuning — P2 ships as observed. `0x8a9438` = 1,000,000.0f
      (`49 74 24 00`), read by exactly ONE instruction (`lfs 2, 0(3)`
      @ 0x8a9470, the shared sleep helper), so 5e5 scales every one
      of the 70 sleep sites (title, menus, gameplay, IO) — global,
      NOT title-only; it does NOT supersede `0x19afbac` (the
      frame-rate TARGET), so BOTH lines ship together under the
      60FPS Unlock toggle: `cheat_60fps = [ bef32, 0x19afbac, 60.0 ]
      + [ bef32, 0x0008a9438, 500000.0 ]`. 500000.0 is FINAL:
      sleep(1/30) round-trips to 16667 µs = exactly one 60 fps
      frame. `0x166c9b8` (the 2^63 round-half-up constant in the
      helper) is a no-touch flag. WATCH ITEM: anything paced by a
      DIFFERENT constant now runs 2× fast — check cutscene
      animation/audio once; if a load ever breaks, patch that
      specific call site, do not revert the rate. Shipped: launcher
      `cheat_60fps` two lines + `PROBE_LINES` back to the single
      0x10100 canary; repo `patches/patch.yml` (two-line 60FPS
      block), `patches/README.md` (Verify: probe `(<- 1)` + 60FPS
      `(<- 2)` = hash `(<- 3)`), `docs/CHEAT-SPECS.md` (60fps row
      patched (finalized); others T-006 tracing; extras → wrong
      layer) synced. **P2 FINAL BOOT-VERIFY CLOSED (2026-11-10,
      22:47:43 boot):** the user's E5 one-toggle test boot satisfied
      it — `('Pipeline Probe (Phase 1)') (<- 1)`,
      `('60FPS Unlock') (<- 2)`, `ppu_loader: PPU executable hash:
      PPU-83096111… (<- 3)`, zero `PAT: Error`/`Skipping`. In-game
      E5 read: framerate box av 57.9–58.0, frametime av 17.3 ms, CPU
      total 18.4–21.4% (PPU 3.3–3.9 / SPU 9.7–11.3 / RSX 5.4–6.2).
      Note: that boot ran BASELINE (PPU Modules Mode Prefer + scale
      150 + P2 live), not H3 — see the E5/H3 entry below; the 22:47
      read is a baseline data point, not an H3 verdict.
      **T-006 PLAN ABSORBED (six slots, MSG-0023):** UE3 keeps
      UnrealScript names (2,396 exec records) — CheatManager ships
      navmesh debug only, NO gameplay cheat. god + one_shot = ONE
      damage-path trace (TakeDamage/CanBeDamaged branch, not a
      global); heavy = field on its own class
      `ABCPlayerController_HeavyShoot`; burst = per-frame gauge
      field; skip_intro = Bink/Kismet skip flag (zero .bik/intro/
      logo strings — Kismet-driven, no movie name to patch);
      extras = probably a save-profile flag, NOT in the module →
      tell the user it's a profile edit, do not patch blind. No
      empty slot gets wired until her addresses land with
      derivations. T-006 branch ff-merged: c64b59d now contained in
      master (tip 6fd9451, comms snapshot MSG-0016..0023).
- [ ] **E5 SKYBOX ARTIFACT — H3 RE-STAGE (2026-11-10, MSG-0033 on the
      bus).** H3 (toggle PPU Modules Mode → Never; one-toggle-per-boot
      rule from Freebuff's MSG-0030) was invalidated by the launcher,
      not by the payload: `configure_engine()` (asuraswrath lines
      594–602) unconditionally rewrites `Core/PPU Modules Mode: Prefer`
      on every GUI Play, so the 22:47 E5 boot ran BASELINE — proof:
      two `ppumod: Hydrated 227 ppumod entries … (227 warm, 0 written)`
      lines (RPCS3.log 5042–5043). The user's read "the red shader
      glitch thingy was less but only a bit, still noticeable" is a
      BASELINE data point (E5 av 57.9–58.0), not an H3 verdict. That
      same log also carries `RSX TODO: Vertex textures … not
      implemented for the shader interpreter.` ×2 — a candidate
      smoking gun on the RSX/interpreter side (would persist under
      Never; relevant to H2/H4). RE-STAGED: `~/.config/rpcs3/config.yml`
      now `PPU Modules Mode: Never` (verified on disk, line 21). GUI
      Play still forces Prefer → the H3 boot is a DIRECT engine
      launch, no launcher:
        cd /home/dio/Games/AsurasWrathRecomp-linux-x86_64
        ./engine/rpcs3 --no-gui --fullscreen disc_extracted
      Same E5 scene as the 3 user screenshots. Gate (I verify on
      boot): NO `ppumod:` hydration lines (Never took effect) +
      patches still clean (probe `(<- 1)`, 60FPS `(<- 2)`, hash
      `(<- 3)`, zero errors). Decision rule (MSG-0030): artifact GONE
      under Never → fault in our ppumod payload (fork's
      compile/hydrate/codegen lane, I take it there); PERSISTS →
      payload exonerated → H2 (Resolution Scale 150→100, `Handle RSX
      Memory Tiling` stays false; keep Never so only scale changes) or
      H4 (stock RPCS3 repro → upstream report). One toggle per boot;
      after the verdict flip back to `Prefer` unless we go straight to
      H2. OPEN ITEM (my lane): user-selectable PPU-mode setting in
      the launcher so the GUI stops stomping manual toggles.
      **H3 VERDICT (23:33 boot, direct launch — payload EXONERATED):**
      gate cleared — ZERO `ppumod:` lines in that session's log (single
      fresh banner; PAT clean: 60FPS `(<- 2)`, probe `(<- 1)`,
      `ppu_loader: PPU executable hash: PPU-83096111… (<- 3)`, zero
      errors). Artifact PERSISTS: mottled red skybox in E5 (screenshot
      #23), framerate box av 57.9 / frametime 17.3 / CPU 22.4%
      (PPU 4.4 / SPU 11.3 / RSX 6.7). Per the MSG-0030 rule:
      PERSISTS under Never → the ppumod payload is exonerated; the
      fault is in the shared emulation/RSX lane, NOT our payload.
      Corroborating smoking gun in the same log: `RSX TODO: Vertex
      textures … not implemented for the shader interpreter.` ×2 at
      boot (0:00:02) and ×2 at the E5 load (0:05:20, lines 2231-2232 /
      121769-121770 of that log) — a vertex-textured skybox shader
      pushed through the interpreter → mottled garbage; candidate root
      cause, and it would persist under ANY PPU mode.
      **H2 STAGED (next boot, 2026-11-10):** `Resolution Scale:
      150 → 100` in `~/.config/rpcs3/config.yml`, `Never` kept so scale
      is the only delta from H3 (one-toggle rule). Same direct-launch
      command + same E5 scene; gate: no ppumod lines, PAT clean,
      mottle state + framerate-box av. If H2 persists → H4
      (stock-RPCS3 repro; if stock mottles too → upstream vertex-
      texture-TODO report) or a shader-mode toggle test (drop the
      interpreter: `Shader Mode: Async Recompiler` — new candidate
      H5, posted to the bus for Freebuff's triage; her call on queue
      order).
      **FIRST H2 ATTEMPT CRASHED AT STARTUP (23:48 launch):** the engine
      SIGSEGV'd ~25 s in, during PPU module-load / early RSX data-heap
      setup (before the title, before E5), so **no H2 mottle read yet**.
      Leading cause = resource flake, NOT the scale change: the engine
      requested a 2 GiB memory lock but `ulimit -l` is only **8192 KB
      (8 MB)** (logged `Failed to set RLIMIT_MEMLOCK size to 2 GiB`), and
      the box is under memory pressure (8.8/15 GiB used, **7.1 GiB in
      swap**). The 23:33 H3 boot (same Re-BAR-on, only scale differed)
      reached E5 fine, so this startup path is not inherently fatal →
      the crash looks transient. **No config change made** (still scale
      100 + Never + Re-BAR on). NEXT: user re-runs the exact same launch
      (close memory hogs first to ease swap). If it crashes the same way
      again (deterministic) → escalate: flip `Use Re-BAR for GPU
      uploads: false` and/or raise the memlock limit to 2 GiB
      (limits.conf / `ulimit -l` as root / CAP_IPC_LOCK), then re-run.
- [ ] D merge gates C1–C4 (when Option D launches)
- [x] **Release v0.9.0 (prototype)** shipped 2026-11-10: tag pushed to
      `demonlorddio/Asuras_wrath_recomp`, GitHub release carries
      `AsurasWrathRecomp-0.9.0-Linux-x86_64.tar.gz` (26 MB, built by
      `scripts/package_release.sh`; sha256 on the release page).

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
- [~] **T-006** (claimed 2026-11-10, in_progress: reachability census in `tasks/T-006.md`)
      candidate addresses for the open cheat slots
      (skip_intro, one_shot, heavy [no heavy-blow cooldown], burst, god,
      + extras ["Unlock All Extras" — launcher slot wired this session]) —
      T-004 left them TBD; `.rodata` sweep already done (4,585 hits), so this
      is a different search (function entry prologues, branch-target patching;
      SPU-side angle dropped per T-006 — no .sprx on the disc, so there is no
      separate SPU image to sweep)
      against `re/disasm/` + `re/ppuanalyser/` (39,248 functions in
      functions.csv; candidates.csv census shows the god/skip/one-shot
      values appear in no swept float constant). User-visible
      "cheats don't work" is these slots being empty, not a pipeline
      fault. User-priority (MSG-0021): start with god/skip_intro, post
      candidate addresses to the bus as they land — Agnes wires +
      boot-verifies each. Claim = flip Status in `re/` task file
      (create `T-006.md`), branch `T-006`.
      **STATE (2026-11-10, MSG-0032/0033):** parser step 1 landed —
      BCGAME.XXX container recipe independently reproduced (314 zlib
      streams; Σout 20,547,928 = sidecar) and name-entry layout
      derived: `int32 BE len | chars incl NUL | 8-byte const
      00 07 00 10 00 00 00 00` (500 consecutive entries share one
      trailer → structural). Walk from 0x2A4F5 → 19,033 names to
      0xAFC79 ('ZValue'); 'None' @ 0x8555D = index 12,776; one
      contiguous table. Export walk BLOCKED on the v841
      FPackageFileSummary field order: the G4DEK doc is not
      retrievable (site 404, GitHub 0 hits, raw 404s), so MSG-0033
      handed over the public-parser-derived stock order (flagged
      NOT-G4DEK) + the observed PS3 header shape (FString "None" @ +12
      early = reorder signal; stock NamesCount/NamesOffset placement
      ruled out; 2-KiB 4-aligned scan shows none of her walk numbers
      in the header; candidate: 4-unaligned 0x000AFCB5 @ +45 ≈
      region_end + 0x3C). Her hold unchanged: no verdict until the
      walk reproduces `Engine.Actor:TakeDamage` non-native with
      bytecode > 0.

Each T-xxx file is self-contained (inputs, outputs, acceptance). Claim = flip
`Status:` in the file to `in_progress (Freebuff)`; leave findings + a report
section at the bottom when done. Branch `T-xxx` per task.

## Omnirush — in maintenance; on return, its queue is pre-built by T-003
- [ ] D2: system-lib packages from `docs/D2-tasklist.md` (one section per library,
      with symbol counts — swarm-ready work packages)
- [ ] D3: PPU↔SPU sync (CSM, reservations, atomics) — the hard 20%, GPT-6-Astra territory
