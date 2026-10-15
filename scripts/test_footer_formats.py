"""Footer format support, using synthetic fixtures and only standard-library code."""
import base64
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from footer_art import discover_footer_art, png_dimensions, webp_dimensions


def png_chunk(kind, payload):
    return (struct.pack('>I', len(payload)) + kind + payload
            + struct.pack('>I', zlib.crc32(kind + payload)))


def png(color, transparency=None, extra=b''):
    """A 3-by-2 all-zero image; palette index/key zero is transparent when set."""
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
    header = png_chunk(b'IHDR', struct.pack('>IIBBBBB', 3, 2, 8, color, 0, 0, 0))
    palette = png_chunk(b'PLTE', b'\x00\x00\x00\xff\xff\xff') if color == 3 else b''
    alpha = png_chunk(b'tRNS', transparency) if transparency is not None else b''
    data = zlib.compress((b'\x00' + bytes(3 * channels)) * 2)
    return b'\x89PNG\r\n\x1a\n' + header + palette + alpha + extra + png_chunk(b'IDAT', data) + png_chunk(b'IEND', b'')


def webp_chunk(kind, payload):
    return kind + struct.pack('<I', len(payload)) + payload + bytes(len(payload) % 2)


def webp(*chunks):
    payload = b'WEBP' + b''.join(chunks)
    return b'RIFF' + struct.pack('<I', len(payload)) + payload


# Synthetic 2-by-1 RGBA pixels [(20, 40, 80, 100), (255, 0, 0, 255)], encoded
# once with Pillow's lossless WebP encoder. Tests and ordinary builds do not
# import Pillow or invoke an encoder. This fixture has a simple VP8L container.
LOSSLESS = base64.b64decode('UklGRiAAAABXRUJQVlA4TBQAAAAvAQAAEA8wKK/4H6iX/YcWMqL/AQ==')
LOSSLESS_CHUNK = LOSSLESS[12:]


def extended_header(flags=0x10, width=2, height=1):
    return webp_chunk(b'VP8X', bytes([flags, 0, 0, 0])
                      + (width - 1).to_bytes(3, 'little') + (height - 1).to_bytes(3, 'little'))


class FooterFormatTests(unittest.TestCase):
    def test_png_alpha_and_transparency_keys(self):
        for color, alpha in ((0, b'\0\0'), (2, b'\0' * 6), (3, b'\0'), (4, None), (6, None)):
            with self.subTest(color=color):
                self.assertEqual(png_dimensions(png(color, alpha)), (3, 2))

    def test_opaque_pngs_and_invalid_transparency_are_rejected(self):
        for color in (0, 2, 3):
            with self.subTest(color=color), self.assertRaisesRegex(ValueError, 'transparent PNG'):
                png_dimensions(png(color))
        for color, alpha in ((0, b'\0'), (2, b'\0'), (3, b'\0' * 3), (4, b'\0'), (6, b'\0')):
            with self.subTest(color=color), self.assertRaisesRegex(ValueError, 'PNG transparency'):
                png_dimensions(png(color, alpha))

    def test_png_animation_markers_are_rejected(self):
        for kind in (b'acTL', b'fcTL', b'fdAT'):
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'static PNG'):
                png_dimensions(png(6, extra=png_chunk(kind, bytes(8))))

    def test_png_truncation_and_crc_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Incomplete PNG'):
            png_dimensions(png(6)[:-12])
        corrupt = bytearray(png(6))
        corrupt[-1] ^= 1
        with self.assertRaisesRegex(ValueError, 'Invalid PNG chunk'):
            png_dimensions(bytes(corrupt))

    def test_lossless_webp_with_and_without_extended_header(self):
        self.assertEqual(webp_dimensions(LOSSLESS), (2, 1))
        self.assertEqual(webp_dimensions(webp(extended_header(), LOSSLESS_CHUNK)), (2, 1))

    def test_webp_animation_flag_and_chunks_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'static WebP'):
            webp_dimensions(webp(extended_header(flags=0x12), LOSSLESS_CHUNK))
        for kind in (b'ANIM', b'ANMF'):
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'static WebP'):
                webp_dimensions(webp(extended_header(), LOSSLESS_CHUNK, webp_chunk(kind, bytes(16))))

    def test_webp_canvas_mismatch_and_truncation_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'dimensions differ'):
            webp_dimensions(webp(extended_header(width=3), LOSSLESS_CHUNK))
        with self.assertRaisesRegex(ValueError, 'Invalid WebP container'):
            webp_dimensions(LOSSLESS[:-1])
        with self.assertRaisesRegex(ValueError, 'Incomplete WebP'):
            webp_dimensions(webp(extended_header()))

    def test_discovery_accepts_every_transparent_encoding_and_checks_provenance(self):
        fixtures = {'palette.png': png(3, b'\0'), 'rgb.PNG': png(2, bytes(6)),
                    'gray.png': png(0, bytes(2)), 'lossless.WEBP': LOSSLESS}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / 'site/footer-backgrounds'
            directory.mkdir(parents=True)
            records = []
            expected = {}
            for name, data in fixtures.items():
                (directory / name).write_bytes(data)
                width, height = (2, 1) if name.endswith('WEBP') else (3, 2)
                expected['footer-backgrounds/' + name] = (width, height)
                records.append({'file': name, 'width': width, 'height': height,
                                'source': 'Synthetic test image', 'processing': 'Fixture defined in this test module'})
            manifest = directory / 'provenance.json'
            manifest.write_text(json.dumps(records))
            self.assertEqual(discover_footer_art(root), expected)
            self.assertEqual(list(discover_footer_art(root)), sorted(expected))
            records[-1]['width'] += 1
            manifest.write_text(json.dumps(records))
            with self.assertRaisesRegex(ValueError, 'dimensions must match provenance'):
                discover_footer_art(root)

    def test_existing_footer_webps_remain_supported(self):
        root = Path(__file__).resolve().parents[1]
        discovered = discover_footer_art(root)
        self.assertEqual(discovered['footer-backgrounds/abyssal.webp'], (2048, 682))
        self.assertEqual(discovered['footer-backgrounds/valley.webp'], (2048, 682))


if __name__ == '__main__':
    unittest.main()
