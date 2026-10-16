"""Discover footer panoramas without a filename list or image-library dependency."""
import json
import hashlib
from pathlib import Path
import struct
import zlib


def png_dimensions(data):
    """Read a static PNG with either an alpha channel or tRNS transparency."""
    if (len(data) < 33 or data[:8] != b'\x89PNG\r\n\x1a\n'
            or data[8:16] != b'\x00\x00\x00\rIHDR'):
        raise ValueError('Invalid PNG header')
    width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', data[16:29])
    depths = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}
    if (depth not in depths.get(color, ()) or compression or filtering
            or interlace not in (0, 1) or not 0 < width < 2**31 or not 0 < height < 2**31):
        raise ValueError('Invalid PNG canvas')
    offset = 8
    palette = None
    transparency = None
    image_data = False
    ended = False
    while offset + 12 <= len(data):
        size = int.from_bytes(data[offset:offset + 4], 'big')
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + size]
        crc = data[offset + 8 + size:offset + 12 + size]
        if len(crc) != 4 or zlib.crc32(kind + payload) != int.from_bytes(crc, 'big'):
            raise ValueError('Invalid PNG chunk')
        if kind in (b'acTL', b'fcTL', b'fdAT'):
            raise ValueError('Expected a static PNG')
        if kind == b'IHDR' and offset != 8:
            raise ValueError('Duplicate PNG header')
        if kind == b'PLTE':
            if palette is not None or image_data or not 0 < size <= 768 or size % 3:
                raise ValueError('Invalid PNG palette')
            palette = size // 3
        if kind == b'tRNS':
            if transparency is not None or image_data:
                raise ValueError('Invalid PNG transparency')
            valid = ((color == 0 and size == 2) or (color == 2 and size == 6)
                     or (color == 3 and palette is not None and 0 < size <= palette))
            if not valid:
                raise ValueError('Invalid PNG transparency')
            transparency = payload
        if kind == b'IDAT':
            image_data = True
        offset += size + 12
        if kind == b'IEND':
            ended = size == 0 and offset == len(data)
            break
    if not ended or not image_data:
        raise ValueError('Incomplete PNG')
    if color == 3 and (palette is None or palette > 2**depth):
        raise ValueError('Invalid PNG palette')
    if color not in (4, 6) and transparency is None:
        raise ValueError('Expected a transparent PNG')
    return width, height


def webp_dimensions(data):
    """Read static transparent extended or simple lossless WebP canvases.

    Container/header checks do not decode compressed pixel data. VP8L keeps its
    dimensions and alpha hint in the bitstream header, without requiring VP8X.
    """
    if (len(data) < 20 or data[:4] != b'RIFF' or data[8:12] != b'WEBP'
            or int.from_bytes(data[4:8], 'little') + 8 != len(data)):
        raise ValueError('Invalid WebP container')
    offset = 12
    canvas = None
    frame = None
    alpha = False
    while offset + 8 <= len(data):
        kind = data[offset:offset + 4]
        size = int.from_bytes(data[offset + 4:offset + 8], 'little')
        payload = data[offset + 8:offset + 8 + size]
        end = offset + 8 + size + size % 2
        if len(payload) != size or end > len(data):
            raise ValueError('Truncated WebP chunk')
        if kind in (b'ANIM', b'ANMF'):
            raise ValueError('Expected a static WebP')
        if kind == b'VP8X':
            if size != 10 or canvas is not None or offset != 12:
                raise ValueError('Invalid extended WebP canvas')
            if payload[0] & 0x02:
                raise ValueError('Expected a static WebP')
            alpha = bool(payload[0] & 0x10)
            canvas = (int.from_bytes(payload[4:7], 'little') + 1,
                      int.from_bytes(payload[7:10], 'little') + 1)
        elif kind == b'VP8L':
            if len(payload) < 5 or payload[0] != 0x2f or frame is not None:
                raise ValueError('Invalid lossless WebP header')
            bits = int.from_bytes(payload[1:5], 'little')
            if bits >> 29:
                raise ValueError('Unsupported lossless WebP version')
            frame = ((bits & 0x3fff) + 1, ((bits >> 14) & 0x3fff) + 1)
            alpha = alpha or bool(bits & (1 << 28))
        elif kind == b'VP8 ':
            if len(payload) < 10 or payload[3:6] != b'\x9d\x01\x2a' or frame is not None:
                raise ValueError('Invalid lossy WebP header')
            frame = (int.from_bytes(payload[6:8], 'little') & 0x3fff,
                     int.from_bytes(payload[8:10], 'little') & 0x3fff)
        offset = end
    if offset != len(data) or frame is None:
        raise ValueError('Incomplete WebP')
    if canvas is not None and canvas != frame:
        raise ValueError('WebP canvas and frame dimensions differ')
    if not alpha:
        raise ValueError('Expected a transparent WebP')
    return canvas or frame

def discover_footer_art(root):
    directory = Path(root) / 'site/footer-backgrounds'
    paths = sorted(p for p in directory.glob('*')
                   if not p.name.startswith('.') and p.suffix.lower() in {'.png', '.webp'}
                   and (p.is_file() or p.is_symlink()))
    records = json.loads((directory / 'provenance.json').read_text(encoding='utf-8'))
    by_name = {record['file']: record for record in records}
    if len(by_name) != len(records):
        raise ValueError('Duplicate footer artwork provenance')
    assets = {}
    for path in paths:
        if path.is_symlink():
            raise ValueError('Symlink footer artwork: ' + path.name)
        record = by_name.get(path.name, {})
        if not record.get('source') or not record.get('processing'):
            raise ValueError('Missing footer artwork provenance: ' + path.name)
        data = path.read_bytes()
        if record.get("sha256") and hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise ValueError("Footer panorama checksum must match provenance: " + path.name)
        try:
            dimensions = webp_dimensions(data) if path.suffix.lower() == '.webp' else png_dimensions(data)
        except ValueError as error:
            raise ValueError(str(error) + ': ' + path.name) from error
        if min(dimensions) <= 0 or dimensions != (record.get('width'), record.get('height')):
            raise ValueError('Footer panorama dimensions must match provenance: ' + path.name)
        assets['footer-backgrounds/' + path.name] = dimensions
    return assets
