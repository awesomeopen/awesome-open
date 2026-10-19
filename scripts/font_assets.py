"""Self-contained default typography, with the original licenses retained."""
import base64
from pathlib import Path


def standalone_font_css(root: Path, serif: str = 'poltawski') -> str:
    vendor = root / 'site/vendor'
    licenses = (vendor / 'FONT-LICENSE.txt').read_text(encoding='utf-8')
    if serif == 'poltawski':
        licenses += '\n' + (vendor / 'serif-preview/poltawski-OFL.txt').read_text(encoding='utf-8')
    rules = []
    for family, weight, path in [
        ('Commit Mono', '200 700', 'commit-mono.woff2'),
        ('Poltawski Nowy', '400', 'serif-preview/poltawski.woff2') if serif == 'poltawski'
        else ('Fraunces', '100 900', 'fraunces.woff2'),
    ]:
        data = base64.b64encode((vendor / path).read_bytes()).decode('ascii')
        rules.append("@font-face {font-family:'%s';font-style:normal;font-weight:%s;"
                     "font-display:swap;src:url(data:font/woff2;base64,%s) format('woff2');}"
                     % (family, weight, data))
    return '/* Bundled font licenses:\n' + licenses + '\n*/\n' + '\n'.join(rules)


def font_asset_url(path: str, root: Path | None = None) -> str:
    """Keep shared typography changes paired across cached visits."""
    import hashlib
    source = (root or Path(__file__).resolve().parents[1]) / 'site' / ('design/tokens.css' if path == 'tokens.css' else path)
    return path + '?v=' + hashlib.sha256(source.read_bytes()).hexdigest()[:16]
