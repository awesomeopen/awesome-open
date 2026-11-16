import { continueRender, delayRender, staticFile } from 'remotion';
import tokens from './generated/tokens.json';

// Colours and type come from site/design/tokens.css through scripts/prepare.mjs.
export const t = tokens;
export const display = "'Poltawski Nowy', Georgia, serif";
export const mono = "'Commit Mono', ui-monospace, monospace";

let loading = null;
export function loadFonts() {
  if (loading || typeof document === 'undefined') return;
  const handle = delayRender('Brand fonts');
  const faces = [new FontFace('Commit Mono', `url(${staticFile('fonts/commit-mono.woff2')})`),
    new FontFace('Poltawski Nowy', `url(${staticFile('fonts/poltawski.woff2')})`)];
  loading = Promise.all(faces.map(face => face.load().then(f => document.fonts.add(f))))
    .then(() => continueRender(handle), error => { console.error(error); continueRender(handle); });
}

// The video's own layer (captions, labels, clock, tags, annotations) is neutral and
// separate from the site's style, so viewers can tell it from page content
// (owner, 2026-11-16; brand/decisions/B-PR343-01.md).
export const v = {
  stage: '#1E2124',
  chip: 'rgba(0, 0, 0, 0.88)',
  text: '#FFFFFF',
  dim: '#B8BDC4',
  edgeSite: '#FFFFFF',
  edgeOther: '#6B7178',
  sans: "'Helvetica Neue', Helvetica, Arial, sans-serif"
};
