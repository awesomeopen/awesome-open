"""Plate details one click away (B-PR146-01).

Each detail is written inline under its box: title, data, then the additional
data. Without script it stays there, in print too. catalog.js hides the panels and
shows the icon trigger, which opens the panel's content in one shared dialog.
Icons come from one sprite per page so 500+ plates do not repeat their markup.
"""
from html import escape
from pathlib import Path
import re

ICONS = Path(__file__).resolve().parent.parent / "site/brand/icons"
PX = {"s": 12, "m": 16}
# Glyphs the plate references. Rows in brand/icons.md list these uses.
SPRITE = (
    *(f"state.{s}-m" for s in ("current", "aged", "partial", "pending", "none", "failed", "unknown")),
    "review.current-m", "control.info-m", "link.external-s", "link.data-s", "link.commit-s",
)
# Signal status (signals.effective_status) to the glyph that restates it.
STATE = {"available": "state.current", "stale": "state.aged", "partial": "state.partial",
         "pending": "state.pending", "unavailable": "state.failed"}


def icon(name, size="m"):
    px = PX[size]
    return (f'<svg class="icon icon-{name.replace(".", "-")}" width="{px}" height="{px}" aria-hidden="true" '
            f'focusable="false"><use href="#icon-{name}-{size}"></use></svg>')


def sprite():
    symbols = []
    for key in SPRITE:
        text = (ICONS / f"{key}.svg").read_text(encoding="utf-8")
        attrs = re.search(r'<svg ([^>]*)>', text)[1]
        view = re.search(r'viewBox="([^"]+)"', attrs)[1]
        body = re.sub(r"^.*?<title>[^<]*</title>|</svg>\s*$", "", text, flags=re.S)
        symbols.append(f'<symbol id="icon-{key}" viewBox="{view}" stroke-linecap="square" '
                       f'stroke-linejoin="miter">{body}</symbol>')
    # Not display:none: masks inside a hidden subtree do not render in every browser.
    return ('<svg class="icon-sprite" width="0" height="0" aria-hidden="true" focusable="false">'
            + "".join(symbols) + "</svg>")


def link(href, text, kind="external", cls=""):
    """A closing link: an external source, a commit, or an evidence file.

    Site evidence files get class evidence-file, which the standalone edition
    points at the footer's single embedded copy instead of repeating the file.
    """
    glyph = {"external": "link.external", "data": "link.data", "commit": "link.commit"}[kind]
    classes = " ".join(filter(None, (cls, "evidence-file" if kind == "data" and not href.startswith("http") else "")))
    attr = f' class="{classes}"' if classes else ""
    return f'<a{attr} href="{escape(href)}">{text}{icon(glyph, "s")}</a>'


def detail(uid, glyph, label, title, body, links=()):
    """Return (trigger, panel). `label`, `title` and `body` are already HTML.

    The visible label stays text; the trigger repeats it next to its icon, so the
    icon never stands for the label alone.
    """
    trigger = (f'<span class="detail-static">{label}</span>'
               f'<button type="button" class="detail-trigger" data-detail="{uid}" aria-haspopup="dialog">'
               f'{icon(glyph)}<span>{label}</span><span class="visually-hidden">: {title}</span></button>')
    closing = f'<p class="detail-links">{" ".join(links)}</p>' if links else ""
    panel = (f'<div class="detail-body" id="{uid}" data-title="{title}">'
             f'<p class="detail-title">{title}</p>{body}{closing}</div>')
    return trigger, panel


def uid(project_id, key):
    return f"detail-{project_id[:12]}-{key}"
