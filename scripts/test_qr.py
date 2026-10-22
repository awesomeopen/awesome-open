import hashlib
import random
import unittest

import qr


def reference_penalty(modules):
    """The original list-based ISO/IEC 18004 penalty, kept to check the fast path."""
    size, score = len(modules), 0
    lines = modules + [list(col) for col in zip(*modules)]
    finder = ([True, False, True, True, True, False, True, False, False, False, False],
              [False, False, False, False, True, False, True, True, True, False, True])
    for line in lines:
        run, prev = 0, None
        for value in line + [None]:
            if value == prev:
                run += 1
            else:
                if run >= 5:
                    score += run - 2
                run, prev = 1, value
        for i in range(size - 10):
            if line[i:i + 11] in finder:
                score += 40
    for y in range(size - 1):
        for x in range(size - 1):
            if modules[y][x] == modules[y][x + 1] == modules[y + 1][x] == modules[y + 1][x + 1]:
                score += 3
    dark = sum(map(sum, modules))
    total = size * size
    score += max(0, (abs(dark * 20 - total * 10) + total - 1) // total - 1) * 10
    return score


class QRTests(unittest.TestCase):
    def test_penalty_matches_reference_on_random_and_biased_grids(self):
        rng = random.Random(18004)
        for size in (21, 25, 45, 57):
            for density in (0.1, 0.5, 0.9):
                grid = [[rng.random() < density for _ in range(size)] for _ in range(size)]
                self.assertEqual(qr._penalty(grid), reference_penalty(grid), (size, density))

    def test_svg_bytes_are_stable_for_fixed_inputs(self):
        # Digests recorded from the encoder before its tables and caches were added.
        expected = {
            'https://awesomeopen.github.io/awesome-open/#project-' + '0' * 64:
                '85a03cfa085e1cc2e0229507728d4119fce3a20ddaae92d10334f61598e5fdf5',
            'Open': '32584a3a9984dd28daa44969f40771e89a35f1b684198d9896ec400fcf9f522b',
        }
        for text, digest in expected.items():
            svg = qr.svg(text, 'QR code: permalink to Example')
            self.assertEqual(hashlib.sha256(svg.encode()).hexdigest(), digest, text)

    def test_cached_templates_are_not_mutated_between_codes(self):
        first = qr.encode('https://example.org/a')
        qr.encode('https://example.org/b')
        self.assertEqual(qr.encode('https://example.org/a'), first)


if __name__ == '__main__':
    unittest.main()
