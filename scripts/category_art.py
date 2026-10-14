"""Validated, local category illustrations; ordinary builds need no image library."""
import base64
import hashlib
from html import escape
import json
from pathlib import Path
import shutil


DISPLAY_SIZE = 48
VARIANTS = ('s', 'm', 'l')


def webp_dimensions(data):
    """Read the extended WebP canvas used by these transparent derivatives."""
    if (len(data) < 30 or data[:4] != b'RIFF' or data[8:12] != b'WEBP'
            or int.from_bytes(data[4:8], 'little') + 8 != len(data)):
        raise ValueError('Invalid WebP container')
    offset = 12
    while offset + 8 <= len(data):
        size = int.from_bytes(data[offset + 4:offset + 8], 'little')
        payload = data[offset + 8:offset + 8 + size]
        if len(payload) != size:
            raise ValueError('Truncated WebP chunk')
        if data[offset:offset + 4] == b'VP8X' and size == 10:
            if not payload[0] & 0x10 or payload[0] & 0x02:
                raise ValueError('Expected a static WebP with alpha')
            return (int.from_bytes(payload[4:7], 'little') + 1,
                    int.from_bytes(payload[7:10], 'little') + 1)
        offset += 8 + size + size % 2
    raise ValueError('Missing extended WebP canvas')


def attach_category_art(catalog, root):
    root = Path(root)
    manifest_path = root / 'site/domains/provenance.json'
    if not manifest_path.exists():
        return  # Older/minimal source trees retain useful text-only navigation.
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('schema_version') != 1 or not isinstance(manifest.get('categories'), dict):
        raise ValueError('Invalid category art manifest')
    categories = {category['id']: category for category in catalog['categories']}
    for cid, record in manifest['categories'].items():
        if cid not in categories:
            raise ValueError('Unknown category artwork ID: ' + cid)
        if record.get('review_status') != 'reviewed-for-integration':
            raise ValueError('Unreviewed category artwork: ' + cid)
        if not isinstance(record.get('alt'), str) or not record['alt'].strip():
            raise ValueError('Missing category artwork description: ' + cid)
        variants = record.get('variants', {})
        if set(variants) != set(VARIANTS):
            raise ValueError('Expected three category artwork sizes: ' + cid)
        widths = []
        for suffix in VARIANTS:
            variant = variants[suffix]
            expected = f'domains/{cid}-{suffix}.webp'
            if variant.get('path') != expected:
                raise ValueError('Invalid category artwork path: ' + cid)
            path = root / 'site' / expected
            if path.is_symlink() or not path.resolve().is_relative_to((root / 'site/domains').resolve()):
                raise ValueError('Unsafe category artwork path: ' + expected)
            data = path.read_bytes()
            if (len(data) != variant.get('bytes')
                    or hashlib.sha256(data).hexdigest() != variant.get('sha256')):
                raise ValueError('Category artwork checksum mismatch: ' + expected)
            dimensions = webp_dimensions(data)
            if dimensions != (variant.get('width'), variant.get('height')):
                raise ValueError('Category artwork dimensions mismatch: ' + expected)
            widths.append(dimensions[0])
        if widths != sorted(set(widths)):
            raise ValueError('Category artwork sizes must increase: ' + cid)
        categories[cid]['artwork'] = {'alt': record['alt'], 'variants': variants}


def category_image(category, offline=False, root=None):
    artwork = category.get('artwork')
    if not artwork:
        return ''
    small = artwork['variants']['s']
    source = small['path']
    medium = artwork['variants']['m']
    end_source = medium['path']
    responsive = ''
    if offline:
        encoded = base64.b64encode((Path(root) / 'site' / source).read_bytes()).decode('ascii')
        source = 'data:image/webp;base64,' + encoded
        end_source = 'data:image/webp;base64,' + base64.b64encode((Path(root) / 'site' / end_source).read_bytes()).decode('ascii')
    else:
        candidates = ', '.join(f'{artwork["variants"][size]["path"]} {artwork["variants"][size]["width"]}w'
                               for size in VARIANTS)
        responsive = f' srcset="{escape(candidates, quote=True)}" sizes="{DISPLAY_SIZE}px"'
    # The adjacent category name supplies the link's accessible name. The image
    # is decorative here; its standalone description remains in provenance.
    return (f'<img class="category-art" src="{escape(source, quote=True)}"{responsive}'
            f' data-end-src="{escape(end_source, quote=True)}" data-end-width="{medium["width"]}" data-end-height="{medium["height"]}"'
            f' style="--category-scale:{small["width"] / DISPLAY_SIZE}"'
            f' width="{small["width"]}" height="{small["height"]}" alt="" aria-hidden="true"'
            ' loading="lazy" decoding="async" fetchpriority="low">')


def copy_category_art(catalog, root, output):
    destination = Path(output) / 'domains'
    shutil.rmtree(destination, ignore_errors=True)
    for category in catalog['categories']:
        for variant in category.get('artwork', {}).get('variants', {}).values():
            path = variant['path']
            destination.mkdir(exist_ok=True)
            shutil.copyfile(Path(root) / 'site' / path, Path(output) / path)
    if destination.exists():
        shutil.copyfile(Path(root) / 'site/domains/provenance.json', destination / 'provenance.json')


def embed_category_art(page, catalog, root):
    # Embed the small navigation icon and medium closing mark, not every
    # responsive candidate. Category selection must also work offline.
    for category in catalog['categories']:
        if category.get('artwork'):
            page = page.replace(category_image(category), category_image(category, offline=True, root=root))
    return page
