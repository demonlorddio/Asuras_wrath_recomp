#!/usr/bin/env python3
"""Build a function map + syscall census for the extracted PPU segments.

  python3 -I scripts/ppu_functions.py [re/segs.json] [out_dir]

Function starts come from the canonical PPC64 prologue `mflr r0`
(0x7c0802a6) — the EBOOT LOAD images have no .symtab, so labels are
`sub_<vaddr>`. Imported libkernel calls are recovered as `sc` sites and the
`li r11, <n>` syscall number in front of them.

Outputs (out_dir defaults to re/ppuanalyser):
  functions.csv   vaddr,size,n_insn,n_sc,n_bl,n_blr,label
  syscalls.csv    call_site,syscall_nr,function_vaddr,function_size
  summary.json    segment layout, counts, syscall histogram, largest functions
"""
import bisect
import json
import os
import sys

import numpy as np

MFLR_R0 = 0x7C0802A6
SC = 0x44000002
BLR = 0x4E800020
BL_MASK, BL_OP = 0xFC000003, 0x48000001
LI_R11_MASK, LI_R11_OP = 0xFFFF0000, 0x39600000


def main(argv):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    segs_path = argv[1] if len(argv) > 1 else os.path.join(root, "re/segs.json")
    out_dir = argv[2] if len(argv) > 2 else os.path.join(root, "re/ppuanalyser")
    os.makedirs(out_dir, exist_ok=True)

    doc = json.load(open(segs_path))
    functions, syscalls, seg_stats = [], [], []

    for seg in doc["load_segments"]:
        vaddr, size = int(seg["vaddr"]), int(seg["filesz"])
        path = os.path.join(root, "re/disasm", seg["out"])
        data = open(path, "rb").read()[:size]
        words = np.frombuffer(data[: len(data) // 4 * 4], dtype=">u4")

        starts = (np.flatnonzero(words == MFLR_R0) * 4).tolist()
        sc_sites = (np.flatnonzero(words == SC) * 4).tolist()

        bounds = starts[1:] + [len(words) * 4]
        for off, end in zip(starts, bounds):
            lo, hi = off // 4, min(end // 4, len(words))
            functions.append((
                vaddr + off, end - off, max(0, (end - off) // 4),
                int(np.count_nonzero(words[lo:hi] == SC)),
                int(np.count_nonzero((words[lo:hi] & BL_MASK) == BL_OP)),
                int(np.count_nonzero(words[lo:hi] == BLR)),
                f"sub_{vaddr + off:x}",
            ))

        for off in sc_sites:
            nr = ""
            for back in range(1, 7):
                j = off // 4 - back
                if j < 0:
                    break
                w = int(words[j])
                if (w & LI_R11_MASK) == LI_R11_OP:
                    nr = w & 0xFFFF
                    break
            syscalls.append((vaddr + off, nr))

        seg_stats.append({
            "vaddr": hex(vaddr), "bytes": len(data),
            "functions": len(starts), "sc": len(sc_sites),
            "bl": int(np.count_nonzero((words & BL_MASK) == BL_OP)),
            "blr": int(np.count_nonzero(words == BLR)),
        })

    starts_sorted = sorted(f[0] for f in functions)
    sizes = {f[0]: f[1] for f in functions}
    with open(os.path.join(out_dir, "functions.csv"), "w") as f:
        f.write("vaddr,size,n_insn,n_sc,n_bl,n_blr,label\n")
        for row in sorted(functions):
            f.write(f"0x{row[0]:x},{row[1]},{row[2]},{row[3]},{row[4]},{row[5]},{row[6]}\n")

    with open(os.path.join(out_dir, "syscalls.csv"), "w") as f:
        f.write("call_site,syscall_nr,function_vaddr,function_size\n")
        for site, nr in sorted(syscalls):
            k = bisect.bisect_right(starts_sorted, site) - 1
            fv = starts_sorted[k] if k >= 0 else None
            f.write(f"0x{site:x},{nr},"
                    + (f"0x{fv:x},{sizes.get(fv, '')}" if fv is not None else "0x0,") + "\n")

    hist = {}
    for _, nr in syscalls:
        if nr != "":
            hist[nr] = hist.get(nr, 0) + 1
    summary = {
        "segments": seg_stats,
        "functions": len(functions),
        "functions_with_sc": sum(1 for f in functions if f[3]),
        "syscall_sites": len(syscalls),
        "syscalls_named": sum(1 for _, nr in syscalls if nr != ""),
        "distinct_syscall_nrs": len(hist),
        "top_syscall_nrs": sorted(hist.items(), key=lambda kv: -kv[1])[:10],
        "largest_prologue_gaps": sorted(
            ((f[0], f[1]) for f in functions), key=lambda t: -t[1])[:5],
    }
    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
