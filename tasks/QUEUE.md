# Queue — 2026-11-09

## Agnes (this session) — owns `~/.config/rpcs3/*` + launcher dir, no one else touches those
- [x] Plan + root-cause evidence → docs/NATIVE-PLAN.md (in repo, synced copy)
- [x] **Phase 1** — patch pipeline: correct v1.2 `patch.yml` + `patch_config.yml`
      (probe patch first), launcher surgery, log-line verification
      (done 2026-11-09: no-op probe `be32 @ PPU vaddr 0x10100`, boot-verified
      both directions — enabled: `PAT: Applied patch … (<- 1)`; disabled:
      warning-variant hash line, 0 applied. Live files under `~/.config/rpcs3`,
      templates in `patches/`, launcher writes `patches_state.json`.)
- [ ] **Phase 2** — consume `re/` outputs (T-002/004), finalize CHEAT-SPECS.md
      (blocked on T-004: needs `re/candidates.csv` + top-5 ranked in
      `docs/CHEAT-SPECS.md`; then fills launcher `CHEAT_LINES`)
- [ ] D merge gates C1–C4 (when Option D launches)

## Freebuff — work these IN ORDER, repo-local only (zero conflict with Agnes)
- [x] **T-002** PPU disassembly pipeline + PPUAnalyser dumps → `re/disasm/`, `re/ppuanalyser/`
      (done 2026-11-09: 39,248 functions, 262 syscall sites, PPU hash MATCH — report at the bottom of T-002.md)
- [x] **T-003** static link 225 objects → import inventory → `re/imports.txt` + `docs/D2-tasklist.md`
      (done 2026-11-09: `ld.lld -r`, 480 imports, 52 lv2 syscalls in 11 namespaces, 417 unresolved vaddrs)
- [ ] **T-004** .rodata candidate sweep → `re/candidates.csv` (+ top-5 rationale in `docs/`)

Each T-xxx file is self-contained (inputs, outputs, acceptance). Claim = flip
`Status:` in the file to `in_progress (Freebuff)`; leave findings + a report
section at the bottom when done. Branch `T-xxx` per task.

## Omnirush — in maintenance; on return, its queue is pre-built by T-003
- [ ] D2: system-lib packages from `docs/D2-tasklist.md` (one section per library,
      with symbol counts — swarm-ready work packages)
- [ ] D3: PPU↔SPU sync (CSM, reservations, atomics) — the hard 20%, GPT-6-Astra territory
