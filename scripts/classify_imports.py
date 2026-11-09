#!/usr/bin/env python3
"""Classify the undefined symbols of the linked PPU module into D2 work packages.

  python3 -I scripts/classify_imports.py [re/imports.txt] [docs/D2-tasklist.md]

Groups:
  sys_<ns>_*          lv2 syscall namespace (what D2 must implement natively)
  __0x<hex>           PPU vaddr referenced by compiled code but defined nowhere
  __*                 native runtime intrinsics (lfqueue/reservation/timer helpers)
  syscall_* / __syscall  syscall trampoline

Outputs re/imports-classified.csv (symbol,group,namespace) and the markdown
tasklist, both derived only from the symbol table — no invented semantics.
"""
import collections
import csv
import os
import re
import sys

GROUP_TITLES = {
    "fs": "Filesystem (`sys_fs_*`)",
    "memory": "Memory (`sys_memory_*`)",
    "mmapper": "Memory mapping (`sys_mmapper_*`)",
    "virtual_memory": "Virtual memory (`sys_virtual_memory_*`)",
    "event": "Event queues / ports (`sys_event_*`)",
    "cond": "Condition variables (`sys_cond_*`)",
    "mutex": "Mutexes (`sys_mutex_*`)",
    "lwmutex": "Lightweight mutexes (`sys_lwmutex_*`)",
    "semaphore": "Semaphores (`sys_semaphore_*`)",
    "rwlock": "Reader/writer locks (`sys_rwlock_*`)",
    "thread": "Threads (`sys_thread_*`)",
    "timer": "Timers (`sys_timer_*`)",
    "time": "Time (`sys_time_*`)",
    "tty": "Console I/O (`sys_tty_*` / `sys_io_*`)",
    "net": "Networking (`sys_net_*`)",
    "spu": "SPU management (`sys_spu_*`)",
    "prx": "Modules (`sys_prx_*`)",
    "ppu": "PPU services (`sys_ppu_*`)",
    "process": "Process (`sys_process_*`)",
    "trace": "Tracing (`sys_trace_*`)",
    "vm": "Virtual memory (`sys_vm_*`)",
}

SYSCALL_RE = re.compile(r"^sys_([a-z0-9]+)_")
ADDR_RE = re.compile(r"^__0x([0-9a-fA-F]+)$")


def classify(sym):
    if ADDR_RE.match(sym):
        return "unresolved_ppu", "unresolved_ppu"
    m = SYSCALL_RE.match(sym)
    if m:
        ns = m.group(1)
        for alias, target in (("io", "tty"), ("lwcond", "cond"), ("lwmutex", "lwmutex")):
            if ns == alias:
                ns = target
        return f"sys_{ns}", ns
    if sym in ("__syscall",) or sym.startswith("syscall_"):
        return "trampoline", "trampoline"
    if sym.startswith("__"):
        return "runtime", "runtime"
    return "other", "other"


def main(argv):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    imports = argv[1] if len(argv) > 1 else os.path.join(root, "re/imports.txt")
    out_md = argv[2] if len(argv) > 2 else os.path.join(root, "docs/D2-tasklist.md")
    syms = [s.strip() for s in open(imports) if s.strip()]

    groups = collections.OrderedDict()
    for s in syms:
        g, ns = classify(s)
        groups.setdefault(g, []).append(s)

    with open(os.path.join(root, "re/imports-classified.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "group", "namespace"])
        for s in syms:
            g, ns = classify(s)
            w.writerow([s, g, ns])

    sys_groups = [g for g in groups if g.startswith("sys_")]
    unresolved = groups.get("unresolved_ppu", [])
    runtime = groups.get("runtime", [])

    lines = [
        "# D2 tasklist — native lv2 surface (from T-003)",
        "",
        f"Derived from `re/imports.txt` ({len(syms)} undefined symbols, each exactly once)",
        "after `ld.lld -r` over the 225 cached PPU objects.",
        "",
        "| group | symbols | meaning |",
        "|---|---|---|",
        f"| lv2 syscalls | {sum(len(groups[g]) for g in sys_groups)} | must be implemented by the native layer |",
        f"| unresolved PPU vaddrs | {len(unresolved)} | referenced by compiled code, defined by no object |",
        f"| runtime intrinsics | {len(runtime)} | provided by the rpcs3 runtime, not game code |",
        f"| syscall trampoline | {len(groups.get('trampoline', []))} | the `sc` path itself |",
    ]
    if "other" in groups:
        lines.append(f"| other | {len(groups['other'])} | unclassified |")
    lines += [
        "",
        "The syscall numbers found in the EBOOT (`re/ppuanalyser/syscalls.csv`, 66 distinct)",
        "are the *other* half of this surface: numbers here, names in the objects. Match",
        "them via rpcs3's syscall table when the numbers are needed.",
        "",
        "## Syscall namespaces",
        "",
    ]

    for g in sorted(sys_groups, key=lambda k: (-len(groups[k]), k)):
        ns = g[4:]
        title = GROUP_TITLES.get(ns, f"`{g}_*`")
        lines.append(f"### {title} — {len(groups[g])} symbol(s)")
        lines.append("")
        for s in sorted(groups[g]):
            lines.append(f"- `{s}`")
        lines.append("")

    lines += [
        f"## Unresolved PPU addresses — {len(unresolved)}",
        "",
        "These are named after the PPU vaddr they refer to (`__0x…`) but no object",
        "defines them. Either the function was not recompiled (data/unsupported)",
        "or the reference crosses an object boundary the recompiler did not emit.",
        "They are the concrete D1 blocker: the native link cannot close without them.",
        "",
        "<details><summary>full list</summary>",
        "",
    ]
    for s in sorted(unresolved, key=lambda x: int(ADDR_RE.match(x).group(1), 16)):
        lines.append(f"- `{s}`")
    lines += ["", "</details>", ""]

    lines += [
        f"## Runtime intrinsics — {len(runtime)}",
        "",
        "Provided by the PPU runtime (atomics, timebase, MMIO, trap), not by D2 game code.",
        "",
    ]
    for s in sorted(runtime):
        lines.append(f"- `{s}`")
    tramp = groups.get("trampoline", [])
    if tramp:
        lines += ["", "## Syscall trampoline", ""]
        for s in sorted(tramp):
            lines.append(f"- `{s}`")
    if "other" in groups:
        lines += ["", "## Other", ""]
        for s in sorted(groups["other"]):
            lines.append(f"- `{s}`")

    open(out_md, "w").write("\n".join(lines) + "\n")
    print(f"{out_md}: {len(syms)} symbols in {len(groups)} groups")
    for g in sorted(groups, key=lambda k: -len(groups[k])):
        print(f"  {g:20s} {len(groups[g])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
