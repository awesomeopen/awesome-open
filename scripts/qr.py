"""Minimal QR Code encoder (byte mode, error correction level M, versions 1-10) rendered as SVG.

Dependency-free so normal builds need nothing new. Follows ISO/IEC 18004 as summarized in
Project Nayuki's reference implementation (MIT); only the subset needed for permalinks is kept.
"""

from functools import lru_cache
from html import escape
import re

# (error-correction codewords per block, [(block count, data codewords per block), ...]) at level M
_EC_M = {
    1: (10, [(1, 16)]), 2: (16, [(1, 28)]), 3: (26, [(1, 44)]), 4: (18, [(2, 32)]),
    5: (24, [(2, 43)]), 6: (16, [(4, 27)]), 7: (18, [(4, 31)]), 8: (22, [(2, 38), (2, 39)]),
    9: (22, [(3, 36), (2, 37)]), 10: (26, [(4, 43), (1, 44)]),
}
_ECL_M_BITS = 0  # format bits for level M


# GF(256) with polynomial 0x11D: multiply through log/antilog tables.
_EXP = [0] * 510
_LOG = [0] * 256
_value = 1
for _i in range(255):
    _EXP[_i] = _EXP[_i + 255] = _value
    _LOG[_value] = _i
    _value <<= 1
    if _value & 0x100:
        _value ^= 0x11D


def _gf_mul(x, y):
    return _EXP[_LOG[x] + _LOG[y]] if x and y else 0


@lru_cache(maxsize=None)
def _rs_divisor(degree):
    result = [0] * (degree - 1) + [1]
    root = 1
    for _ in range(degree):
        for j in range(degree):
            result[j] = _gf_mul(result[j], root)
            if j + 1 < degree:
                result[j] ^= result[j + 1]
        root = _gf_mul(root, 0x02)
    return tuple(result)


def _rs_remainder(data, divisor):
    result = [0] * len(divisor)
    for b in data:
        factor = b ^ result.pop(0)
        result.append(0)
        if factor:
            log = _LOG[factor]
            for i, coef in enumerate(divisor):
                if coef:
                    result[i] ^= _EXP[_LOG[coef] + log]
    return tuple(result)


def _alignment_positions(version):
    if version == 1:
        return []
    count = version // 7 + 2
    step = (version * 8 + count * 3 + 5) // (count * 4 - 4) * 2
    return [6] + [version * 4 + 10 - i * step for i in reversed(range(count - 1))]


def _codewords(data, version):
    ec_len, groups = _EC_M[version]
    capacity = sum(n * k for n, k in groups)
    count_bits = 8 if version <= 9 else 16
    bits = [0, 1, 0, 0] + [(len(data) >> i) & 1 for i in reversed(range(count_bits))]
    for byte in data:
        bits += [(byte >> i) & 1 for i in reversed(range(8))]
    bits += [0] * min(4, capacity * 8 - len(bits))
    bits += [0] * (-len(bits) % 8)
    padded = [int(''.join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    pad = 0xEC
    while len(padded) < capacity:
        padded.append(pad)
        pad ^= 0xEC ^ 0x11
    blocks, offset, divisor = [], 0, _rs_divisor(ec_len)
    for n, k in groups:
        for _ in range(n):
            block = padded[offset:offset + k]
            offset += k
            blocks.append((block, _rs_remainder(block, divisor)))
    longest = max(len(b) for b, _ in blocks)
    result = [b[i] for i in range(longest) for b, _ in blocks if i < len(b)]
    result += [e[i] for i in range(ec_len) for _, e in blocks]
    return result


def _format_bits(mask):
    data = (_ECL_M_BITS << 3) | mask
    rem = data
    for _ in range(10):
        rem = (rem << 1) ^ ((rem >> 9) * 0x537)
    return ((data << 10) | rem) ^ 0x5412


def _version_bits(version):
    rem = version
    for _ in range(12):
        rem = (rem << 1) ^ ((rem >> 11) * 0x1F25)
    return (version << 12) | rem


@lru_cache(maxsize=None)
def _function_template(version):
    modules, reserved = _function_patterns(version)
    return tuple(map(tuple, modules)), tuple(map(tuple, reserved))


@lru_cache(maxsize=None)
def _mask_flips(version, mask):
    """Data-module positions each mask inverts; identical for every code of a version."""
    _, reserved = _function_template(version)
    rule = _MASKS[mask]
    return tuple((y, x) for y, row in enumerate(reserved) for x, taken in enumerate(row)
                 if not taken and rule(x, y))


def _function_patterns(version):
    size = version * 4 + 17
    modules = [[False] * size for _ in range(size)]
    reserved = [[False] * size for _ in range(size)]

    def put(x, y, dark):
        modules[y][x] = dark
        reserved[y][x] = True

    for i in range(size):
        put(6, i, i % 2 == 0)
        put(i, 6, i % 2 == 0)
    for cx, cy in ((3, 3), (size - 4, 3), (3, size - 4)):
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                x, y = cx + dx, cy + dy
                if 0 <= x < size and 0 <= y < size:
                    put(x, y, max(abs(dx), abs(dy)) not in (2, 4))
    positions = _alignment_positions(version)
    last = len(positions) - 1
    for i, cx in enumerate(positions):
        for j, cy in enumerate(positions):
            if (i, j) in ((0, 0), (0, last), (last, 0)):
                continue
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    put(cx + dx, cy + dy, max(abs(dx), abs(dy)) != 1)
    # Reserve format areas (filled per mask) and the always-dark module.
    for i in range(9):
        reserved[8][i] = reserved[i][8] = True
    for i in range(8):
        reserved[8][size - 1 - i] = reserved[size - 1 - i][8] = True
    put(8, size - 8, True)
    if version >= 7:
        bits = _version_bits(version)
        for i in range(18):
            dark = (bits >> i) & 1 == 1
            a, b = size - 11 + i % 3, i // 3
            put(a, b, dark)
            put(b, a, dark)
    return modules, reserved


def _draw_format(modules, mask):
    size = len(modules)
    bits = _format_bits(mask)
    bit = lambda i: (bits >> i) & 1 == 1
    for i in range(6):
        modules[i][8] = bit(i)
    modules[7][8] = bit(6)
    modules[8][8] = bit(7)
    modules[8][7] = bit(8)
    for i in range(9, 15):
        modules[8][14 - i] = bit(i)
    for i in range(8):
        modules[8][size - 1 - i] = bit(i)
    for i in range(8, 15):
        modules[size - 15 + i][8] = bit(i)
    modules[size - 8][8] = True


_MASKS = [
    lambda x, y: (x + y) % 2 == 0, lambda x, y: y % 2 == 0, lambda x, y: x % 3 == 0,
    lambda x, y: (x + y) % 3 == 0, lambda x, y: (x // 3 + y // 2) % 2 == 0,
    lambda x, y: x * y % 2 + x * y % 3 == 0, lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0,
    lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0,
]


_RUNS = re.compile(r'0{5,}|1{5,}')
_FINDERS = re.compile(r'(?=10111010000|00001011101)')  # overlapping matches
_BITS = bytes.maketrans(b'\x00\x01', b'01')


def _penalty(modules):
    size, score = len(modules), 0
    rows = [bytes(row).translate(_BITS).decode('ascii') for row in modules]
    columns = [''.join(column) for column in zip(*rows)]
    # One pass over all rows and columns; the separator ends every run and pattern.
    lines = '2'.join(rows + columns)
    score += sum(len(run) - 2 for run in _RUNS.findall(lines))
    score += 40 * len(_FINDERS.findall(lines))
    # 2x2 same-colour blocks: compare neighbouring columns of two rows as bit masks.
    width = (1 << (size - 1)) - 1
    values = [int(row, 2) for row in rows]
    for upper, lower in zip(values, values[1:]):
        same = ~(upper ^ lower)
        score += 3 * (same & (same >> 1) & ~(upper ^ (upper >> 1)) & width).bit_count()
    dark = sum(row.count('1') for row in rows)
    total = size * size
    score += max(0, (abs(dark * 20 - total * 10) + total - 1) // total - 1) * 10
    return score


def encode(text):
    """Return the module matrix (list of rows of bools) for a UTF-8 string."""
    data = text.encode('utf-8')
    for version in range(1, 11):
        _, groups = _EC_M[version]
        capacity_bits = sum(n * k for n, k in groups) * 8
        if 4 + (8 if version <= 9 else 16) + len(data) * 8 <= capacity_bits:
            break
    else:
        raise ValueError('Text too long for the supported QR versions')
    template, reserved = _function_template(version)
    base = [list(row) for row in template]
    size = len(base)
    codewords = _codewords(data, version)
    bits = [(cw >> (7 - i)) & 1 for cw in codewords for i in range(8)]
    index = 0
    right = size - 1
    while right >= 1:
        if right == 6:
            right = 5
        for vert in range(size):
            for j in range(2):
                x = right - j
                upward = (right + 1) & 2 == 0
                y = size - 1 - vert if upward else vert
                if not reserved[y][x] and index < len(bits):
                    base[y][x] = bits[index] == 1
                    index += 1
        right -= 2
    best = None
    for mask in range(len(_MASKS)):
        candidate = [row[:] for row in base]
        for y, x in _mask_flips(version, mask):
            candidate[y][x] = not candidate[y][x]
        _draw_format(candidate, mask)
        score = _penalty(candidate)
        if best is None or score < best[0]:
            best = (score, candidate)
    return best[1]


def svg(text, label):
    """A compact, scalable SVG with horizontal runs merged; no quiet zone (the page provides it)."""
    modules = encode(text)
    size = len(modules)
    path = []
    for y, row in enumerate(modules):
        x = 0
        while x < size:
            if row[x]:
                start = x
                while x < size and row[x]:
                    x += 1
                path.append(f'M{start} {y}h{x - start}v1h-{x - start}z')
            else:
                x += 1
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" shape-rendering="crispEdges" role="img" '
            f'aria-label="{escape(label, quote=True)}"><path fill="#111820" d="{"".join(path)}"/></svg>\n')
