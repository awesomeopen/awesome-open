"""Discover footer panoramas without a filename list or image-library dependency."""
import json
from pathlib import Path
import struct
import zlib

from category_art import webp_dimensions

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
        if path.suffix.lower() == '.webp':
            dimensions = webp_dimensions(data)
        else:
            if (len(data) < 33 or data[:8] != b'\x89PNG\r\n\x1a\n'
                    or data[8:16] != b'\x00\x00\x00\rIHDR' or data[25] not in (4, 6)):
                raise ValueError('Expected a static transparent PNG: ' + path.name)
            offset = 8
            ended = False
            while offset + 12 <= len(data):
                size = int.from_bytes(data[offset:offset + 4], 'big')
                chunk = data[offset + 4:offset + 8 + size]
                crc = data[offset + 8 + size:offset + 12 + size]
                if len(crc) != 4 or zlib.crc32(chunk) != int.from_bytes(crc, 'big'):
                    raise ValueError('Invalid PNG chunk: ' + path.name)
                if chunk[:4] == b'acTL':
                    raise ValueError('Expected a static PNG: ' + path.name)
                offset += size + 12
                if chunk[:4] == b'IEND':
                    ended = size == 0 and offset == len(data)
                    break
            if not ended:
                raise ValueError('Incomplete PNG: ' + path.name)
            dimensions = struct.unpack('>II', data[16:24])
        if min(dimensions) <= 0 or dimensions != (record.get('width'), record.get('height')):
            raise ValueError('Footer panorama dimensions must match provenance: ' + path.name)
        assets['footer-backgrounds/' + path.name] = dimensions
    return assets
