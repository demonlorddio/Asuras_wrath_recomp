#!/usr/bin/env python3
"""Wrap a raw big-endian PPC64 code blob in a minimal ELF so llvm-objdump can
disassemble it (the host has no ppc binutils and objdump has no -b binary).

  python3 -I scripts/mkppcelf.py <in.bin> <out.o> <vaddr> [size]

Produces an ET_REL ELF64, big-endian, EM_PPC64 (21), with one .text section at
<vaddr>. Sections: NULL, .text, .shstrtab — no program headers.
"""
import struct
import sys


def build(data: bytes, vaddr: int) -> bytes:
    ehsize = 64
    text_off = ehsize
    shstr = b"\0.text\0.shstrtab\0"
    shstr_off = text_off + len(data)
    shoff = shstr_off + len(shstr)
    shnum = 3

    ident = b"\x7fELF" + bytes([2, 2, 1, 0]) + b"\0" * 8  # 64-bit, MSB, v1
    ehdr = ident + struct.pack(
        ">HHIQQQIHHHHHH",
        1,    # e_type = ET_REL
        21,   # e_machine = EM_PPC64
        1,    # e_version
        0,    # e_entry
        0,    # e_phoff
        shoff,
        0,    # e_flags
        ehsize,
        0,    # e_phentsize
        0,    # e_phnum
        64,   # e_shentsize
        shnum,
        2,    # e_shstrndx
    )

    def sh(name, stype, flags, addr, off, size, align):
        return struct.pack(
            ">IIQQQQIIQQ", name, stype, flags, addr, off, size, 0, 0, align, 0
        )

    sections = (
        b"\0" * 64                                        # SHN_UNDEF
        + sh(1, 1, 6, vaddr, text_off, len(data), 4)       # .text PROGBITS AX
        + sh(7, 3, 0, 0, shstr_off, len(shstr), 1)         # .shstrtab STRTAB
    )
    return ehdr + data + shstr + sections


def main(argv):
    if len(argv) < 4 or len(argv) > 5:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    src, dst, vaddr = argv[1], argv[2], int(argv[3], 0)
    data = open(src, "rb").read()
    if len(argv) == 5:
        data = data[: int(argv[4], 0)]
    open(dst, "wb").write(build(data, vaddr))
    print(f"{dst}: {len(data)} bytes .text @ 0x{vaddr:x}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
