#!/usr/bin/env python3
"""Generate a multi-resolution Windows .ico from the source PNG.

Uses PySide6 (already a project dependency) to scale each icon size, then
assembles a standard ICO container with the standard library. The small sizes
are stored as BMP/DIB and the 256 pixel size as PNG: this is the layout the
Windows shell needs. Explorer, the Start menu, search and the taskbar read the
small BMP entries, while modern Windows reads the PNG entry for the large icon.
Storing every size as PNG (the previous approach) left those small contexts
with no entry they could render, so the app showed a blank icon in search.

No Pillow or other extra dependency is needed. Run from the project root:

    python tools/make_icon.py

The output is ``assets/o7debrief.ico``, which buildexe.py and buildinstaller.py
embed as the executable's Windows PE icon. Re-run this whenever the source
``assets/o7Debrief.png`` changes.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, Qt
from PySide6.QtGui import QImage

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SOURCE_PNG = _PROJECT_ROOT / "assets" / "o7Debrief.png"
_TARGET_ICO = _PROJECT_ROOT / "assets" / "o7debrief.ico"

# Standard Windows icon sizes to embed, smallest to largest. Sizes below the
# PNG threshold are written as BMP/DIB so the shell can render them at small
# dimensions; the largest is a PNG to keep the file small.
_SIZES = (16, 32, 48, 64, 128, 256)
_PNG_THRESHOLD = 256

# ICO container constants (see the BMP/ICO file-format specification).
_ICONDIR = "<HHH"
_ICONDIRENTRY = "<BBBBHHII"
_ICONDIR_SIZE = struct.calcsize(_ICONDIR)
_ICONDIRENTRY_SIZE = struct.calcsize(_ICONDIRENTRY)
_BITMAPINFOHEADER = "<IiiHHIIiiII"
_RESERVED = 0
_TYPE_ICON = 1
_COLOR_COUNT = 0
_PLANES = 1
_BIT_COUNT = 32
_BI_RGB = 0
_DIB_HEADER_SIZE = 40
# An icon DIB stores the colour bitmap then a 1 bpp mask, so the header height
# is twice the image height.
_MASK_HEIGHT_FACTOR = 2
_BYTES_PER_PIXEL = 4
_ALIGN_BITS = 32
_ALIGN_BYTES = 4
# A 256-pixel dimension is encoded as the byte value 0 in an ICONDIRENTRY.
_MAX_DIMENSION = 256
_DIMENSION_AS_ZERO = 0
_PNG_FORMAT = "PNG"


def _scaled(image: QImage, size: int) -> QImage:
    """Return the source scaled smoothly to a ``size`` square, in ARGB32."""
    scaled = image.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return scaled.convertToFormat(QImage.Format.Format_ARGB32)


def _png_bytes(image: QImage, size: int) -> bytes:
    """Return the PNG bytes of ``image`` scaled to ``size`` square."""
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    _scaled(image, size).save(buffer, _PNG_FORMAT)
    data = bytes(buffer.data())
    buffer.close()
    return data


def _bmp_bytes(image: QImage, size: int) -> bytes:
    """Return the BMP/DIB bytes (header, colours and mask) for ``size`` square.

    The colour rows are bottom-up 32 bpp BGRA, matching the ARGB32 buffer on a
    little-endian host. The AND mask is all zero, so transparency comes from the
    alpha channel rather than the mask.
    """
    icon = _scaled(image, size)
    width = icon.width()
    height = icon.height()
    header = struct.pack(
        _BITMAPINFOHEADER,
        _DIB_HEADER_SIZE,
        width,
        height * _MASK_HEIGHT_FACTOR,
        _PLANES,
        _BIT_COUNT,
        _BI_RGB,
        _RESERVED,
        _RESERVED,
        _RESERVED,
        _RESERVED,
        _RESERVED,
    )
    raw = bytes(icon.constBits())
    bytes_per_line = icon.bytesPerLine()
    row_bytes = width * _BYTES_PER_PIXEL
    colours = bytearray()
    for row in range(height - 1, -1, -1):
        start = row * bytes_per_line
        colours += raw[start : start + row_bytes]
    mask_stride = ((width + _ALIGN_BITS - 1) // _ALIGN_BITS) * _ALIGN_BYTES
    mask = bytes(mask_stride * height)
    return header + bytes(colours) + mask


def _dimension_byte(size: int) -> int:
    """Return the ICONDIRENTRY dimension byte (0 stands for 256)."""
    return _DIMENSION_AS_ZERO if size >= _MAX_DIMENSION else size


def _blob_for(image: QImage, size: int) -> bytes:
    """Return one size encoded: BMP/DIB below the PNG threshold, else PNG."""
    if size >= _PNG_THRESHOLD:
        return _png_bytes(image, size)
    return _bmp_bytes(image, size)


def make_icon() -> int:
    """Build the multi-size .ico from the source PNG. Returns a process code."""
    if not _SOURCE_PNG.exists():
        print(f"[make_icon] source PNG not found: {_SOURCE_PNG}", file=sys.stderr)
        return 1
    image = QImage(str(_SOURCE_PNG))
    if image.isNull():
        print(f"[make_icon] could not load image: {_SOURCE_PNG}", file=sys.stderr)
        return 1

    blobs = [(_dimension_byte(size), _blob_for(image, size)) for size in _SIZES]
    header = struct.pack(_ICONDIR, _RESERVED, _TYPE_ICON, len(blobs))
    offset = _ICONDIR_SIZE + _ICONDIRENTRY_SIZE * len(blobs)
    entries = bytearray()
    for dimension, blob in blobs:
        entries += struct.pack(
            _ICONDIRENTRY,
            dimension,
            dimension,
            _COLOR_COUNT,
            _RESERVED,
            _PLANES,
            _BIT_COUNT,
            len(blob),
            offset,
        )
        offset += len(blob)
    payload = b"".join(blob for _, blob in blobs)
    _TARGET_ICO.write_bytes(header + bytes(entries) + payload)
    print(
        f"[make_icon] wrote {_TARGET_ICO} "
        f"({_TARGET_ICO.stat().st_size} bytes, {len(blobs)} sizes)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(make_icon())
