#!/usr/bin/env python3
"""Build a preview-only A/B composition from the current generated OpenTofu plate."""
import argparse
from html.parser import HTMLParser
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

class PlateParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.depth = 0
        self.parts = []
        self.done = False
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if not self.depth and not self.done and tag == 'div' and 'plate-broad' in attrs.get('class', ''):
            self.depth = 1
        elif self.depth and tag == 'div':
            self.depth += 1
        if self.depth:
            self.parts.append(self.get_starttag_text())
    def handle_endtag(self, tag):
        if self.depth:
            self.parts.append(f'</{tag}>')
            if tag == 'div':
                self.depth -= 1
                self.done = self.depth == 0
    def handle_data(self, data):
        if self.depth: self.parts.append(data)
    def handle_entityref(self, name):
        if self.depth: self.parts.append(f'&{name};')
    def handle_charref(self, name):
        if self.depth: self.parts.append(f'&#{name};')

def build(output):
    output = Path(output)
    parser = PlateParser()
    parser.feed((output/'index.html').read_text())
    if not parser.done: raise ValueError('OpenTofu plate missing')
    plate = ''.join(parser.parts).replace('href="#', 'href="./#')
    # Its heading lives outside the extracted plate in the ordinary ledger.
    plate = plate.replace('aria-labelledby="name-', 'data-original-labelledby="name-')
    template = (ROOT/'site/design/specimen-comparison.html').read_text()
    template = template.replace('__PLATE__', plate).replace('__CONTOUR__', (ROOT/'site/design/specimen-contour.svg').read_text())
    (output/'specimen-comparison.html').write_text(template)
    print('Specimen comparison: specimen-comparison.html')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    build(p.parse_args().output)
