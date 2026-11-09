#!/usr/bin/env python3
"""Sweep the PPU LOAD segments for cheat-relevant constants (T-004).

  python3 -I scripts/rodata_sweep.py [re/segs.json] [re/ppuanalyser/functions.csv]

Patterns are big-endian PPU encodings (30.0f, 60.0f, 1/30, 1/60, int 30/60,
1.0f, 0.5f, -1.0f). For every hit the script records:
  - segment + vaddr + pattern id + 32-byte hex context
  - in_code: hit lies inside a prologue-derived function range (so it is an
    immediate inside instructions, NOT patchable .rodata)
  - refs: how many times code builds that address via lis/addis(+ori) and
    loads/stores through it — a data constant that code reads

Outputs re/candidates.csv (all hits) and re/references.csv (address refs).
Nothing outside re/ is written; this is analysis only (no patches).
"""
import bisect
import csv
import json
import os
import struct
import sys

import numpy as np

# IEEE-754 big-endian, verified with struct.pack('>f', x). The T-004 spec's bytes
# were wrong by 2x (0x42f00000 is 120.0f, 0x3d2aaaab is 1/24); correct values here.
PATTERNS = [
    ("f32_30.0", "41f00000", 4, "be32/bef32"),
    ("f32_60.0", "42700000", 4, "be32/bef32"),
    ("f64_30.0", "403e000000000000", 8, "be64"),
    ("f64_60.0", "404e000000000000", 8, "be64"),
    ("f32_1over30", "3d088889", 4, "be32"),
    ("f32_1over60", "3c888889", 4, "be32"),
    ("f32_1over24", "3d2aaaab", 4, "be32"),
    ("f32_1over6", "3e2aaaab", 4, "be32"),
    ("f32_120.0", "42f00000", 4, "be32"),
    ("i32_30", "0000001e", 4, "be32"),
    ("i32_60", "0000003c", 4, "be32"),
    ("f32_1.0", "3f800000", 4, "be32/bef32"),
    ("f32_0.5", "3f000000", 4, "be32/bef32"),
    ("f32_-1.0", "bf800000", 4, "be32"),
]

# PPU64 ELFv1 uses r2 as the data/TOC base. Observed access
# `lwz 7, -24984(2)` resolves to 0x19a9e68 (the 120.0f table entry) only for
# this base, which is also inside the RW load segment (0x1940000-0x19eea80).
BASE_R2 = 0x019B0000

# opcodes with a 16-bit displacement through a base register
LOADS_STORES = {
    32: "lwz", 33: "lwzu", 34: "lbz", 35: "lbzu", 36: "stw", 37: "stwu",
    38: "stb", 39: "stbu", 40: "lhz", 41: "lhzu", 42: "lha", 43: "lhau",
    44: "sth", 45: "sthu", 50: "lfd", 51: "lfdu", 52: "stfd", 53: "stfdu",
    58: "ld", 59: "ldu", 60: "lwa", 61: "std", 62: "stdu",
}


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def main(argv):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    segs_path = argv[1] if len(argv) > 1 else os.path.join(root, "re/segs.json")
    fns_path = (argv[2] if len(argv) > 2
                else os.path.join(root, "re/ppuanalyser/functions.csv"))

    doc = json.load(open(segs_path))
    fn_ranges = []
    if os.path.exists(fns_path):
        for row in csv.DictReader(open(fns_path)):
            a, sz = int(row["vaddr"], 0), int(row["size"])
            if sz:
                fn_ranges.append((a, a + sz))
    fn_ranges.sort()
    fn_starts = [a for a, _ in fn_ranges]

    def in_code(addr):
        k = bisect.bisect_right(fn_starts, addr) - 1
        return k >= 0 and fn_ranges[k][0] <= addr < fn_ranges[k][1]

    hits, ref_rows, refs_all, ref_kinds = [], [], {}, {}
    seg_ranges = []
    for seg in doc["load_segments"]:
        base, size = int(seg["vaddr"]), int(seg["filesz"])
        data = open(os.path.join(root, "re/disasm", seg["out"]), "rb").read()[:size]
        seg_ranges.append((base, base + len(data)))
        words = np.frombuffer(data[: len(data) // 4 * 4], dtype=">u4")

        for pat_id, hexpat, _plen, pat_type in PATTERNS:
            needle = bytes.fromhex(hexpat)
            start = 0
            while True:
                off = data.find(needle, start)
                if off < 0:
                    break
                start = off + 1
                ctx = data[max(0, off - 16): off + 16].hex()
                hits.append({
                    "segment": seg["out"], "vaddr": base + off,
                    "offset": off, "pattern": pat_id, "type": pat_type,
                    "value": hexpat, "in_code": int(in_code(base + off)),
                    "context_hex": ctx,
                })

        # code-built data addresses: lis/addis rX,hi ... lwz/stw rY,lo(rX)
        lis_idx = np.flatnonzero((words >> 26) == 15)
        refs = {}
        for i in lis_idx.tolist():
            w = int(words[i])
            ra = (w >> 16) & 0x1F
            rd = (w >> 21) & 0x1F
            if ra != 0 or rd == 0:      # lis rX, imm
                continue
            hi = (w & 0xFFFF) << 16
            for j in range(i + 1, min(i + 7, len(words))):
                w2 = int(words[j])
                op = w2 >> 26
                if op == 24 and ((w2 >> 16) & 0x1F) == rd:   # ori rY, rX, imm
                    addr = hi | (w2 & 0xFFFF)
                    refs[addr] = refs.get(addr, 0) + 1
                    ref_rows.append((base + j * 4, addr, "addr"))
                if op in LOADS_STORES and ((w2 >> 16) & 0x1F) == rd:
                    addr = (hi + s16(w2 & 0xFFFF)) & 0xFFFFFFFFFFFFFFFF
                    if addr < (1 << 32):
                        refs[addr] = refs.get(addr, 0) + 1
                        kind = LOADS_STORES[op]
                        ref_rows.append((base + j * 4, addr, kind))
                        ref_kinds.setdefault(addr, []).append(kind)

        # r2-relative data accesses (the dominant form for .rodata)
        for j, w2 in enumerate(words.tolist()):
            op = w2 >> 26
            if op not in LOADS_STORES or ((w2 >> 16) & 0x1F) != 2:
                continue
            addr = BASE_R2 + s16(w2 & 0xFFFF)
            refs[addr] = refs.get(addr, 0) + 1
            kind = LOADS_STORES[op]
            ref_rows.append((base + j * 4, addr, kind))
            ref_kinds.setdefault(addr, []).append(kind)
        refs_all.update(refs)

    for h in hits:
        h["refs"] = refs_all.get(h["vaddr"], 0)
        k = ref_kinds.get(h["vaddr"], [])
        h["ref_ops"] = ",".join(f"{m}*{k.count(m)}" for m in sorted(set(k)))

    out = os.path.join(root, "re/candidates.csv")
    cols = ["vaddr", "segment", "pattern", "type", "value", "in_code", "refs",
            "ref_ops", "context_hex"]
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for h in sorted(hits, key=lambda x: (x["pattern"], -x["refs"], x["vaddr"])):
            w.writerow({**h, "vaddr": f"0x{h['vaddr']:x}"})

    with open(os.path.join(root, "re/references.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ref_site", "target", "kind"])
        for site, addr, kind in sorted(ref_rows):
            w.writerow([f"0x{site:x}", f"0x{addr:x}", kind])

    print(f"{out}: {len(hits)} hits, {len(refs_all)} distinct referenced addresses")
    by = {}
    for h in hits:
        by.setdefault(h["pattern"], [0, 0, 0])
        by[h["pattern"]][0] += 1
        by[h["pattern"]][1] += 1 if h["in_code"] else 0
        by[h["pattern"]][2] += 1 if h["refs"] else 0
    for p, (n, code, ref) in sorted(by.items()):
        print(f"  {p:12s} hits={n:5d} in_code={code:5d} referenced={ref:4d}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
