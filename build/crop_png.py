"""Crop a PNG without third-party libraries.

Written for the card screenshots: the reference host draws its own title bar
inside the window, so a capture carries ~42 px of chrome that a store listing
should not show. Pure stdlib (zlib + struct) so it runs on the managed Python
with no install step.

Usage: python crop_png.py <src.png> <dst.png> <skip_top_px>
"""

import struct
import sys
import zlib


def read_png(path):
    d = open(path, "rb").read()
    if d[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit("not a PNG")
    pos = 8
    idat = b""
    w = h = bd = ct = None
    while pos < len(d):
        ln = struct.unpack(">I", d[pos : pos + 4])[0]
        typ = d[pos + 4 : pos + 8]
        data = d[pos + 8 : pos + 8 + ln]
        if typ == b"IHDR":
            w, h, bd, ct, _comp, _filt, inter = struct.unpack(">IIBBBBB", data)
            if inter:
                raise SystemExit("interlaced PNG not supported")
        elif typ == b"IDAT":
            idat += data
        elif typ == b"IEND":
            break
        pos += 12 + ln
    return w, h, bd, ct, zlib.decompress(idat)


def paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def unfilter(raw, w, h, bpp):
    stride = w * bpp
    out = bytearray()
    prev = bytearray(stride)
    pos = 0
    for _y in range(h):
        f = raw[pos]
        pos += 1
        line = bytearray(raw[pos : pos + stride])
        pos += stride
        if f == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif f == 3:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 255
        elif f == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                c = prev[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + paeth(a, prev[i], c)) & 255
        elif f != 0:
            raise SystemExit("unknown filter %d" % f)
        out += line
        prev = line
    return bytes(out)


def write_png(path, w, h, ct, pixels):
    bpp = {0: 1, 2: 3, 4: 2, 6: 4}[ct]
    stride = w * bpp
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += pixels[y * stride : (y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    out = b"\x89PNG\r\n\x1a\n"
    out += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ct, 0, 0, 0))
    out += chunk(b"IDAT", comp)
    out += chunk(b"IEND", b"")
    open(path, "wb").write(out)


def main():
    src, dst, skip = sys.argv[1], sys.argv[2], int(sys.argv[3])
    w, h, bd, ct, raw = read_png(src)
    print("src: %dx%d bitdepth=%d colortype=%d" % (w, h, bd, ct))
    if bd != 8:
        raise SystemExit("only 8-bit PNG supported")
    bpp = {0: 1, 2: 3, 4: 2, 6: 4}[ct]
    pixels = unfilter(raw, w, h, bpp)
    stride = w * bpp
    new_h = h - skip
    cropped = pixels[skip * stride :]
    write_png(dst, w, new_h, ct, cropped)
    print("dst: %dx%d -> %s" % (w, new_h, dst))


if __name__ == "__main__":
    main()
