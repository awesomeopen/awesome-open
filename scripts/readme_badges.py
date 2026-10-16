"""Small offline README badges using the catalog's canonical project identities."""

from html import escape


COUNT_PATH = "assets/readme/specimen-count.svg"


def specimen_count(source):
    # Import lazily: the catalog itself imports the README validation module.
    # Reuse its URL rules rather than maintaining another identity definition.
    from build_catalog import canonical_url
    from render_readme import ENTRY, validate_source

    validate_source(source)
    return len({canonical_url(match[2]) for line in source.splitlines()
                if (match := ENTRY.fullmatch(line))})


def flat_badge(label):
    """An accessible, unrounded Prussian-blue label with deterministic sizing."""
    width = len(label) * 7 + 20
    text = escape(label, quote=True)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" '
            f'role="img" aria-label="{text}">\n'
            f'  <title>{text}</title>\n'
            f'  <rect width="{width}" height="20" fill="#0B2546"/>\n'
            f'  <text x="{width / 2:g}" y="14" fill="#fff" text-anchor="middle" '
            f'font-family="DejaVu Sans Mono,monospace" font-size="11">{text}</text>\n'
            '</svg>\n')


def count_badge(source):
    # Singular is the owner's requested badge wording for every count.
    return flat_badge(f"{specimen_count(source)} specimen")
