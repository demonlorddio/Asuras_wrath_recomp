# T-005 — where the 30 fps cap actually lives (results + next probe)

Trigger: MSG-0014 — the `0x19afbac` 30.0f→60.0f data patch applied cleanly and
in-game fps stayed at 30.36 with total CPU at 15%. That refuted T-004's
low–medium-confidence data candidate, so this task asks two questions:

1. Is the cap a **fixed-duration sleep** (the timer-syscall hypothesis)?
2. Is it one of the **six code-side `1/30` sites** (the D-line bake hypothesis)?

**Answers: no and no.** Details below, then two one-word probes that
discriminate between the remaining hypotheses, then the trace recipe.

Inputs: `re/disasm/seg0.txt` (T-002 listing), `re/ppuanalyser/functions.csv`,
`re/ppuanalyser/syscalls.csv`, `re/references.csv`, both LOAD segments.
Produced by `scripts/t005_pacing.py` (`pools` / `sleep` modes);
`re/t005-sleep-sites.csv` is its `sleep` output joined to function ranges.

## 1. There is no 33 ms sleep in the game

`sys_timer_usleep` (141) is called directly at 21 sites in the listing. Every
immediate argument, read from the `li 3, N` that feeds the `sc`:

| argument (µs) | count | shape |
|---|---|---|
| 10, 30 | 5 | yield after a failed try-lock |
| 300 | 2 | double-checked init poll |
| 800, 1000 | 3 | worker-thread park |
| 1200 | 3 | stream/IO poll |
| ≥ 2000 | 0 | — |

The largest fixed sleep in the binary is **1.2 ms**, i.e. ~40× short of one
30 fps frame. `sys_timer_sleep` (142) is called once, with a garbage-decoded
argument, and is not on any per-frame path.

The game almost never calls `sys_timer_usleep` directly. It has a helper at
**`0x8a9458`**:

```
lfs  2, 0(0x8a9438)      ; rate = 1e6  (f32 0x49742400 @ 0x8a9438)
fmuls 1, f1, f2          ; seconds -> microseconds
fsub / fsel / fctidz     ; round to nearest integer
cmpldi 3, 30 ; li 3, 30  ; 30 us floor
li 11, 141 ; sc          ; sys_timer_usleep
```

So every `sleep(seconds)` in the game funnels through one function with
**70 call sites** (`re/t005-sleep-sites.csv`). Their arguments:

* **dynamic** — `fmr 1, f31` after loading a float field out of a heap object
  (the majority: worker/IO waits on a per-object interval);
* **constants** — `0.0`, `0.01`, `1.0` seconds (loaded from `.text` pools at
  `0x13648`, `0x889088`, `0x62cf0`, `0x89b1c0`).

**No call site passes 1/30 s or 1/60 s.** If the engine paced frames by
sleeping, this table would show a 0.0333 argument — it does not.

## 2. The six `1/30` words are dead pools, not a frame delta

T-004 found `3D088889` (1/30f) exactly 6 times, all "code-side". They are GCC
literal pools emitted at function boundaries, all with the same neighbours
(e.g. at `0xfed528`: `1/30f, 0x41EFFFFFFFE00000, 0x41E00000`). `lis`+`addi`
readers (`scripts/t005_pacing.py pools`, which also handles the
`lis`+`lfs offset(rX)` form that T-004's `lis`+`ori` sweep missed):

| pool | readers | what the reader does |
|---|---|---|
| `0x76ae54` | `0x76b028`, `0x76b0cc` | `fnmsubs`/`fsub`/`fsel`/`fsel` on three consecutive floats — Bezier/curve evaluation, not timing |
| `0xfed528` | `0x87919c` | `sub_87917c`: while global `0x1aafc2c` is 0, do init work and `sleep(1/30)` — a **startup wait**, exits once the flag is set |
| `0x157138`, `0x754480`, `0x879174`, `0x10b3554` | none | unreferenced |

So the "patch the six 1/30 sites" plan is closed: two live uses are a curve
parameter and an init wait. Patching either would not raise fps. Nothing here
needs a D-line bake.

## 3. Do not patch `0x160bbf0` — it is the timebase scaler

T-004 flagged `0x160bbf0` as a decoy (117 `lfd` readers, 8-byte value = the
double `2^32`, with `fcfid` following). Now we know why: it is the constant the
**high-resolution timestamp helper** uses to convert `mftb` ticks to double
seconds:

```
sub_879034:  mftb 3, 268
             ... split into hi/lo, fcfid, fmadd
             lfd 1, 0x160bbf0            ; 4294967296.0 = 2^32
             fmul 1, 1, 2                ; * (1/79800000) style scale
             stfd 1, 0x1a75088           ; global "now", double seconds
```

The only code reference to `0x1a75088` is `0x8895c4` (`lfd`). Patching the
2^32 word would break every timer in the game, so it is explicitly prohibited
in the cheat lines below.

## 4. Probes: two one-word writes that decide the next phase

Neither of these is a 60 fps cheat. They are **diagnostics** whose outcome
selects which fix is worth building, and both are trivially reversible
(`be32` back to the original word, no state).

### P1 — make the sleep helper a no-op

```yaml
- [ be32, 0x0008a9458, 0x4e800020 ]   # sleep(seconds) -> blr
```

Original word at `0x8a9458` is `f8 21 ff 81` (`stdu 1, -128(1)`).

* **fps jumps well past 30** → the cap is a sleep after all (most likely the
  dynamic-argument worker path feeding the frame budget). Then go to P2 to
  land on 60 instead of "as fast as possible", and to §5 to find the caller.
* **fps unchanged** → no sleep paces the frame. The remaining wait is an
  event: an RSX flip/vblank or a semaphore. Go to §5's second half. Do not
  keep polling sleeps — that road is now closed.

Side effect of P1: init/IO waits become busy polls, so loading may spin CPU.
That is why it is a probe, not the cheat.

### P2 — halve every sleep duration

```yaml
- [ bef32, 0x0008a9438, 500000.0 ]    # rate 1e6 -> 5e5: every sleep is half as long
```

Value **must** be a decimal float (`bin_patch.cpp:808`, MSG-0013). Use this
only if P1 overshoots, to check whether fps scales with the sleep length — a
linear fps response is the fingerprint of a frame-budget sleep and tells us
the exact call site to bake. If fps does not scale, the cap is not sleep-shaped
and this probe is also a no-op.

### Reading the result (the failure mode that already bit us)

MSG-0017: the first "60.00 fps" P1 read was **not** a P1 boot. The launcher GUI
regenerates the live patch files from its in-memory line list on every Play
press, so a GUI opened before the probe was wired silently rewrote the config
back to the refuted 60FPS block; the boot applied only 1 line (`<- 2)` hash) and
the instantaneous title-loop number showed 60 while the **framerate-box
average** stayed at ~31.8, i.e. the baseline. Two rules follow:

* the routing number is the box average (`av:`), never the big instant FPS;
* confirm from the engine log that the probe actually applied (expected
  `probe <- 1)`/`<- 2)` **and** a changed hash) before believing any fps read.

Probe lines must be handed to Agnes as **launcher list entries** (its
`PROBE_LINES`), not as hand edits of the live `patch.yml` — a hand edit is
wiped on the next Play press.

### Never patch, for the record

`0x160bbf0` (2^32 timebase scaler, §3), `0x19ad530` / `0x19a8d88` (physics
1/60 steps, T-004 §4), `0x19afbac` (already refuted in game), and the four dead
1/30 pools (§2).

## 5. If P1 changes nothing: the trace recipe

The 30 fps with 15% CPU means the PPU thread blocks. Attach with the RPCS3
debugger (PPU thread) and break on these, in order:

1. **`0x8a9458`** — how often per second, and what `f1` is. Confirms/denies
   sleep pacing without patching anything.
2. **`0x879034`** — the timestamp helper. Watch `0x1a75088` (double seconds)
   and `0x8895c4` (its only reader). If that reader runs once per frame, its
   caller is the frame loop; if it runs once per *two* frames, the cap is a
   tick divider there.
3. **Stub `0x16037c0`** — an import thunk (`lwz` slot at `0x195a3d0`, then
   `bctrl`), called 16× and repeatedly *immediately before* sleeps
   (`0x21d1b8`, `0x88911c`, `0x89b3a8`, `0x8791c8`, …). Whatever import that
   slot resolves to is part of the wait path. Slot index is the fastest way to
   name it: `0x195a3d0` is one entry in the same table T-003 enumerated, so
   index = `(0x195a3d0 - table_base) / 8`.
4. If the block is a **flip/vblank wait**, the fix is not a code constant at
   all: it is either the present path (2 presents per 3 vsyncs, etc.) or a
   config-level question for Agnes. Report that back rather than guessing.

## 6. Status

No proven 60 fps patch yet, and this document does not claim one. (A "60.00
fps" P1 read briefly circulated and was withdrawn as a P1-off baseline — see
MSG-0017 and §4; treat any pre-MSG-0017 fps figure in this repo as baseline.) What it does
provide is:

* empirical closure of two hypotheses (fixed sleep; code-side 1/30 bake),
  each with a table of evidence rather than an assertion;
* the single choke point for all game timing (`sleep` at `0x8a9458`, rate word
  `0x8a9438`, 70 call sites in `re/t005-sleep-sites.csv`);
* two one-word, reversible probes with pre-declared outcomes, so one boot
  answers the remaining question;
* an explicit no-patch list so the next agent does not re-find the decoys.
