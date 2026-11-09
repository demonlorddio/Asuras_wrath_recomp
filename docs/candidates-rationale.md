# T-004 — .rodata candidate rationale (top-5 per cheat slot)

Input: `re/candidates.csv` (4,585 hits), `re/references.csv` (124,520 code→data
references), produced by `scripts/rodata_sweep.py` from the two EBOOT LOAD
segments (`seg_000000010000.bin`, `seg_000001940000.bin`).
Context: `re/disasm/seg0.txt` / `seg1.txt` (T-002) + `re/ppuanalyser/functions.csv`.

**Headline result: no `.rodata` constant can be shown to be the 30 → 60 fps cap.**
The 30.0f value appears 86 times, but 82 of those hits lie inside
prologue-derived function ranges (i.e. code-side), and there is no address
anywhere holding a 30/60 pair. Section 4 lists what was ruled out; section 5
proposes the follow-up probe. The top-5 below are the ranked *places to probe*,
not proven addresses — confidence is stated per row.

## 1. The spec's encodings were wrong (corrected here)

`tasks/T-004.md` (and the encoding block that was in `docs/CHEAT-SPECS.md`)
list byte patterns that decode to different values. Every entry was wrong by a
factor of 2, 4 or 46. Verified with `struct.pack('>f'/' >d', x)`; the sweep now
uses the right-hand column.

| value | spec bytes | what the spec bytes actually are | correct bytes |
|---|---|---|---|
| 30.0f | `42F00000` | 120.0f | `41F00000` |
| 60.0f | `42C00000` | 96.0f | `42700000` |
| 1/30 s f32 | `3D2AAAAB` | 0.0416667 = 1/24 | `3D088889` |
| 1/60 s f32 | `3E2AAAAB` | 0.166667 = 1/6 | `3C888889` |
| 30.0 f64 | `4047000000000000` | 46.0 | `403E000000000000` |
| 60.0 f64 | `4057000000000000` | 92.0 | `404E000000000000` |

The spec's `1/60 = 1/30 ÷ 2` arithmetic assumed `3D2AAAAB` was 1/30 and
then *added* to the exponent instead of subtracting (`3E2AAAAB` = 1/6, not
1/60). A sweep with the spec bytes would have searched for 120.0/96.0/1÷24/1÷6
and reported them as frame timing — all 4,490 first-pass hits were re-run after
the correction. `1/24` (`3D2AAAAB`) and `1/6` (`3E2AAAAB`) are kept as separate
pattern ids because they do occur in the binary.

## 2. Reference detection (how "referenced" is established)

Two address-construction forms are recognised in code:

* `lis rX, hi` within 6 instructions of `ori rY, rX, lo` or of a D-form
  load/store through `rX` (opcodes 32–62) → `target = hi*65536 + sign_extend(lo)`.
* r2-relative accesses (`lwz/stw/lfs/lfd/ld/std …, disp(r2)`), the dominant
  form for globals on PPU64 ELFv1. `BASE_R2 = 0x019B0000`, inferred because
  `lwz 7, -24984(2)` resolves to `0x19a9e68` — the table entry holding 120.0f —
  and `0x19b0000` lies inside the RW segment (0x1940000–0x19eea80).

Each reference records the access mnemonic (`ref_ops`, e.g. `lwz*3`), which is
what separates a real data read from a coincidental byte match. Caveat:
listings of data blobs also decode as plausible instructions, so a single
reference is weak evidence and is checked by hand below (see `0x16803b0`).

## 3. Top-5 for `cheat_60fps` (ranked probes)

All five hold a 30.0f word (`41F00000`) in a data segment. "Old → New" is the
4-byte swap that the cheat proposes.

| # | Address | Segment | Old → New | Evidence (code context) | Confidence |
|---|---|---|---|---|---|
| 1 | `0x19afbac` | seg1 | `41F00000` → `42700000` | Only 30.0f handed to a callee as an argument: `0xe0d078: lwz 4, -1108(2)` → `bl 0xf31c58`, return value tested by `cmpwi 7, 3, 0` — a setter/query taking the value as a parameter, not a table copy. Neighbours `256.0, 16.0, 0.6931 (ln 2)` — a small engine-parameter pool. | low–medium |
| 2 | `0x19cbe10` | seg1 | `41F00000` → `42700000` | Compact gameplay-tuning pool: `2, 10.0, 1.0, 0.1, 30.0, 2.0, 5.0, 15.0`. Layout matches a tunables struct rather than a random float table. | low |
| 3 | `0x19cbe68` | seg1 | `41F00000` → `42700000` | Second pool 0x58 bytes later: `1, 0.999, -1, 5.0, 30.0, 0.0, 0.0015, 0.0015`. Tuning-shaped, no direct reader found. | low |
| 4 | `0x19a8384` | seg1 | `41F00000` → `42700000` | Magic-constants pool: `0.001, 1e6, 180.0, π, 30.0, 45.0, 110.0, 80.0`. **Its one recorded reference (`0x16803b0`) is a misdecode of a data blob** (`81 82 83 84 …` byte ramp), so treat as unreferenced. | low |
| 5 | `0x160bbf0` | seg0 | (reject) | 117 references, the highest of any 30.0f hit, but every reader is `lfd` — the 8-byte record is the **double 2^32**, and the following instruction is `fcfid` (int→float conversion). The 30.0f match is the high half of that double. | rejected |

Nothing in this list is proven to be the frame cap. Row 1 is the only candidate
whose code context shows the value being *used as a value*; rows 2–4 are
context-only. Row 5 is documented so nobody re-finds it and believes it.

## 4. What was ruled out (negative results)

* **No 30/60 adjacency.** Every 30.0f data hit was compared against all 60.0f
  and 120.0f hits: none is within 0x100 bytes of another. A frame-cap table
  would normally hold both (30 Hz and 60 Hz modes) — there is no such table.
* **The cap is probably code-side.** 82 of 86 `41F00000` hits fall inside
  prologue-derived function ranges — the constant is materialised in
  instructions/immediates, not read from `.rodata`. A data patch therefore
  cannot reach it, which is exactly the constraint that made the fabricated
  `patch.yml` addresses look plausible but never work.
* **`int32 30` is not the cap.** All 10 data hits of `0000001E` are inside
  ascending integer tables (`12,14,15,17,30,32,33,35,40`) or pointer arrays —
  index/limit tables, no reader references them.
* **The `1/60` constants in data are physics, not rendering.** `0x19ad530`
  sits in the pool `0.157, 0.1, 1.75, 4.0, 0.0167, -0.2, 0.0, -9.8` (`-9.8` =
  gravity), and its neighbours `0x19ad52c/530/534` are fed one-float-per-call
  into `0xf32408` — a parameter-application loop. `0x19a8d88` (`1/60, -0.2,
  NaN`) is the integration step of a `mtctr` loop at `0x1513a24`
  (`lwz 10, -29304(2)` … `frsp 1, 0`). Changing either would retime physics,
  not the renderer — do not patch these for a 60 fps cheat.
* **`1/30` never occurs as data at all** (6 hits, all code-side); only `1/60`
  does. An engine that runs physics at a fixed 1/60 step is consistent with a
  30 fps render cap implemented in code.

## 5. Other cheat slots: no defensible candidate

The hard rule is that raw hits without context do not belong in the rationale.
For the remaining slots that leaves nothing to rank:

| Slot | Why no candidate |
|---|---|
| `cheat_skip_intro` | Needs a movie/state branch or flag, not a numeric constant. `.rodata` sweep cannot express it; needs string xrefs to the BIK filename or a state-machine enum (T-005 work). |
| `cheat_one_shot`, `cheat_heavy`, `cheat_burst`, `cheat_god` | All are gameplay values stored in runtime objects allocated at load, not in `.rodata`: `1.0f`/`0.5f`/`-1.0f` each have 1,000+ hits and no slot-specific context, and damage/gauge caps live in heap structs written after init. A static sweep cannot point at them. |
| `cheat_extras` | Unlock gates are bitfields in save/profile data or in the PSN/trophy layer; no constant distinguishes them. |

Fabricating an address here is exactly root cause R4, so these stay `TBD`.

## 6. Recommended next probe (for Agnes / Phase 2)

1. **Runtime read-trace on the frame delta**, not a static search: attach to the
   PPU thread, break on the timer read (`cellKb`/`sys_timer_usleep` consumers),
   and watch which constant the frame-time clamp compares against. The T-002
   syscall table already lists the 66 syscalls by number.
2. **If the cap is a code immediate**, the cheat must move to the D-line "bake"
   path (value patched in EBOOT + `--ppumod-build`), since the spec's
   data-only rule cannot apply. Two code-side shapes to look for: `cmpwi` with
   30 against a computed frame counter, or a `1/30` constant materialised by
   `lis/ori` into a float register (6 such `3D088889` sites exist, all code).
3. `BASE_R2 = 0x19B0000` and `re/references.csv` are reusable for T-005 —
   any `.rodata` address can now be checked for readers in one grep.
