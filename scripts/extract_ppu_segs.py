#!/usr/bin/env python3
"""T-002 / Phase 1.1 — extract PPU LOAD segments from the reconstructed EBOOT.elf
and reproduce the RPCS3 PPU-executable SHA1 exactly as
rpcs3/Emu/Cell/PPUModule.cpp::ppu_load_exec does it.

Run from the repo, -I (isolated), args-only. NEVER reads game files directly —
input is the `EBOOT.elf` that `rpcs3 --decrypt` produced in a scratch dir.

PPU hash algorithm (authoritative, PPUModule.cpp:2299-2457):
  sha1_starts
  for every program header (all e_phnum, in file order):
      update p_type   (4B BIG-endian — raw file bytes; see "Hash big-endian
                       values" comment at PPUModule.cpp:2345)
      update p_flags  (4B BIG-endian)
      if p_type==LOAD(1) and p_memsz != 0:
          update p_vaddr (8B BIG-endian)
          update p_memsz (8B BIG-endian)
          update bin     (p_filesz bytes read at p_offset in the file)
  sha1_finish -> digest
  key = "PPU-" + digest(40 hex)

NOTE on endianness: on x86-64 the be_t<u32>/be_t<u64> phdr fields hold their
RAW file bytes in big-endian order (se_t stores byte-swapped on LE hosts).
So the hash feeds BIG-endian values, NOT host-little-endian. Feeding
little-endian is the original bug that produced the false
19854d3d... MISMATCH.
"""
import argparse
import hashlib
import json
import os
import struct
import sys

LOAD = 0x1
EXPECTED_DEFAULT = "83096111daff850cc92b637aec1780c4079e1c58"


def u16be(b, off):
    return struct.unpack_from(">H", b, off)[0]


def u32be(b, off):
    return struct.unpack_from(">I", b, off)[0]


def u64be(b, off):
    return struct.unpack_from(">Q", b, off)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("elf_path", help="path to reconstructed EBOOT.elf (BE ppc64 ELF)")
    ap.add_argument("out_dir", help="re/ output dir (will create re/disasm)")
    ap.add_argument("--expected", default=EXPECTED_DEFAULT,
                    help="expected 40-hex PPU digest to verify against")
    a = ap.parse_args()

    with open(a.elf_path, "rb") as f:
        data = f.read()

    # --- ehdr (ELF64, big-endian) ---
    if data[:4] != b"\x7fELF":
        sys.exit(f"FATAL: not an ELF (first 4 = {data[:4]!r})")
    ei_class = data[4]
    ei_data = data[5]
    ei_osabi = data[7]
    e_type = u16be(data, 0x10)
    e_machine = u16be(data, 0x12)
    e_entry = u64be(data, 0x18)
    e_phoff = u64be(data, 0x20)
    e_shoff = u64be(data, 0x28)
    e_phentsize = u16be(data, 0x36)
    e_phnum = u16be(data, 0x38)
    e_shentsize = u16be(data, 0x3A)
    e_shnum = u16be(data, 0x3C)

    print(f"[elf] class={ei_class} data={ei_data}(2=BE) os_abi={ei_osabi:#04x} "
          f"type={e_type} machine={e_machine} entry={e_entry:#x} "
          f"phoff={e_phoff} phentsize={e_phentsize} phnum={e_phnum} "
          f"shoff={e_shoff} shentsize={e_shentsize} shnum={e_shnum} filesize={len(data)}")
    if ei_class != 2 or ei_data != 2:
        sys.exit("FATAL: expected 64-bit big-endian ELF")

    # --- parse all program headers ---
    phdrs = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        if off + e_phentsize > len(data):
            sys.exit(f"FATAL: phdr[{i}] at {off} exceeds file size {len(data)}")
        p_type = u32be(data, off + 0)
        p_flags = u32be(data, off + 4)
        p_offset = u64be(data, off + 8)
        p_vaddr = u64be(data, off + 16)
        p_paddr = u64be(data, off + 24)
        p_filesz = u64be(data, off + 32)
        p_memsz = u64be(data, off + 40)
        p_align = u64be(data, off + 48)
        phdrs.append(dict(idx=i, p_type=p_type, p_flags=p_flags, p_offset=p_offset,
                          p_vaddr=p_vaddr, p_paddr=p_paddr, p_filesz=p_filesz,
                          p_memsz=p_memsz, p_align=p_align))

    print("\n[phdrs]")
    for h in phdrs:
        print(f"  [{h['idx']}] type={h['p_type']} flags={h['p_flags']:#x} "
              f"offset={h['p_offset']:#x} vaddr={h['p_vaddr']:#x} paddr={h['p_paddr']:#x} "
              f"filesz={h['p_filesz']:#x} memsz={h['p_memsz']:#x} align={h['p_align']:#x}")

    # --- reproduce PPU SHA1 exactly ---
    sha = hashlib.sha1()
    disasm_dir = os.path.join(a.out_dir, "disasm")
    os.makedirs(disasm_dir, exist_ok=True)
    load_segs = []

    for h in phdrs:
        # unconditional: p_type + p_flags for every phdr (BIG-endian raw bytes)
        sha.update(h["p_type"].to_bytes(4, "big"))
        sha.update(h["p_flags"].to_bytes(4, "big"))

        if h["p_type"] == LOAD and h["p_memsz"] != 0:
            lo, hi = h["p_offset"], h["p_offset"] + h["p_filesz"]
            if hi > len(data):
                sys.exit(f"FATAL: phdr[{h['idx']}] bin range {lo:#x}-{hi:#x} exceeds file {len(data)}")
            blob = data[lo:hi]
            sha.update(h["p_vaddr"].to_bytes(8, "big"))
            sha.update(h["p_memsz"].to_bytes(8, "big"))
            sha.update(blob)

            segname = f"seg_{h['p_vaddr']:012x}.bin"
            segpath = os.path.join(disasm_dir, segname)
            with open(segpath, "wb") as out:
                out.write(blob)
            load_segs.append(dict(
                idx=h["idx"], vaddr=h["p_vaddr"], memsz=h["p_memsz"],
                filesz=h["p_filesz"], flags=h["p_flags"], p_type=h["p_type"],
                file=h["p_offset"], file_end=hi, bytes=len(blob),
                out=segname, blob_sha1=hashlib.sha1(blob).hexdigest(),
            ))
            print(f"  -> {segname} ({len(blob)} B)  blob_sha1={hashlib.sha1(blob).hexdigest()}")

    digest = sha.hexdigest()
    ppu_key = "PPU-" + digest
    match = digest.lower() == a.expected.lower()

    print(f"\n[ppu-hash] {ppu_key}")
    print(f"[expected] PPU-{a.expected}")
    print(f"[verdict]  {'MATCH' if match else 'MISMATCH'}")

    # --- write outputs ---
    with open(os.path.join(a.out_dir, "ppu-hash.txt"), "w") as f:
        f.write(f"{ppu_key}\n")
        f.write(f"expected: PPU-{a.expected}\n")
        f.write(f"verdict:  {'MATCH' if match else 'MISMATCH'}\n")

    segs_json = dict(
        source_elf=a.elf_path,
        file_size=len(data),
        entry=e_entry,
        os_abi=f"0x{ei_osabi:02x}",
        phnum=e_phnum,
        ppu_hash=ppu_key,
        expected=f"PPU-{a.expected}",
        match=bool(match),
        phdrs=phdrs,
        load_segments=load_segs,
    )
    with open(os.path.join(a.out_dir, "segs.json"), "w") as f:
        json.dump(segs_json, f, indent=2)
    print(f"\n[out] {a.out_dir}/ppu-hash.txt, {a.out_dir}/segs.json, {disasm_dir}/ ({len(load_segs)} LOAD segs)")

    if not match:
        sys.exit(2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
