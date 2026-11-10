#!/usr/bin/env python3
"""T-005 frame-pacing tracer.

Two jobs, both over the T-002 disassembly listing (re/disasm/seg0.txt):

1. `pools` -- find the code that materialises each `1/30f` literal pool in
   .text (GCC puts the word at a function boundary and loads it with
   `lis rA,hi` + `addi rA,rA,lo`). T-004's reference sweep only matched
   `lis`+`ori`, so these pools had no recorded readers.

2. `sleep` -- list every call site of the sleep primitive at 0x8a9458
   (seconds -> `sys_timer_usleep(round(sec*1e6))`, floor 30 us) together with
   the float argument setup that precedes it, so the 1/30-second callers can
   be separated from short yields.

Usage:
  scripts/t005_pacing.py pools [addr ...]
  scripts/t005_pacing.py sleep
"""
import re
import sys

LISTING = "re/disasm/seg0.txt"
SLEEP_FN = 0x8A9458

# 1/30f (0x3D088889) occurrences inside the .text segment.
DEFAULT_POOLS = [0x157138, 0x754480, 0x76AE54, 0x879174, 0xFED528, 0x10B3554]

LINE = re.compile(r"^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2} )+)\s*\t(.*)$")


def parse(m):
    return int(m.group(1), 16), m.group(3).strip()


def hi_lo(target):
    hi = ((target + 0x8000) >> 16) & 0xFFFF
    lo = target & 0xFFFF
    if lo >= 0x8000:
        lo -= 0x10000
    return hi, lo


def pools(addrs):
    wanted = {a: hi_lo(a) for a in addrs}
    ring = []
    with open(LISTING, errors="replace") as f:
        for ln in f:
            m = LINE.match(ln.rstrip("\n"))
            if not m:
                continue
            addr, insn = parse(m)
            ring.append((addr, insn))
            if len(ring) > 12:
                ring.pop(0)
            # Two materialisation forms: `lis rA,hi` + `addi rA,rA,lo`, and
            # `lis rA,hi` + a D-form access with a small offset (`lfs f,lo(rA)`).
            am = re.match(r"addi (\d+), (\d+), (-?\d+)$", insn)
            dm = re.match(r"[a-z.]+ (?:\d+, )?(-?\d+)\((\d+)\)$", insn)
            if am and am.group(1) == am.group(2):
                dst, lo, form = am.group(1), int(am.group(3)), "addi"
            elif dm:
                lo, dst, form = int(dm.group(1)), dm.group(2), "dform"
            else:
                continue
            for back_addr, back in reversed(ring[:-1]):
                lm = re.match(r"lis (\d+), (\d+)$", back)
                if not lm:
                    continue
                if lm.group(1) != dst:
                    continue
                target = (int(lm.group(2)) << 16) + (lo & 0xFFFFFFFF)
                target &= 0xFFFFFFFF
                if target in wanted and wanted[target][0] == int(lm.group(2)):
                    print(
                        f"0x{addr:x},0x{target:x},{form}: lis {back}|{insn},"
                        f"@{back_addr:#x}"
                    )
                break


def sleep_sites():
    ring = []
    with open(LISTING, errors="replace") as f:
        for ln in f:
            m = LINE.match(ln.rstrip("\n"))
            if not m:
                continue
            addr, insn = parse(m)
            ring.append((addr, insn))
            if len(ring) > 40:
                ring.pop(0)
            if not re.match(r"bl 0x%x( |$)" % SLEEP_FN, insn):
                continue
            print(f"### call 0x{addr:x}")
            # Show the 12 instructions that build the f1 argument; a 1/30
            # argument shows up as an lfs from a .text pool address.
            for a, i in ring[-13:]:
                print(f"    {a:#x}: {i}")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("pools", "sleep"):
        print(__doc__)
        return 1
    if sys.argv[1] == "pools":
        addrs = [int(x, 0) for x in sys.argv[2:]] or DEFAULT_POOLS
        pools(addrs)
    else:
        sleep_sites()
    return 0


if __name__ == "__main__":
    sys.exit(main())
