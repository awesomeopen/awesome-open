import { interpolate } from 'remotion';
import { mono, t } from '../theme.js';

// Code read from the repository by scripts/prepare.mjs, typed in over the first
// 60% of the overlay and then held. The header names the file and lines.
export const CodePanel = ({ overlay, snippet, s }) => {
  const total = snippet.rows.reduce((n, row) => n + row.reduce((m, tok) => m + tok.content.length, 0) + 1, 0);
  let left = Math.round(interpolate(s, [overlay.from, overlay.from + (overlay.to - overlay.from) * 0.6], [0, total],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }));
  return (
    <div style={{ position: 'absolute', left: 48, top: 120, width: 1100, background: t.paper, border: `2px solid ${t.ink}`,
      boxShadow: t.shadow, fontFamily: mono }}>
      <div style={{ background: t.blueprint, color: t.paper, fontSize: 20, padding: '8px 16px' }}>
        {snippet.file} · lines {snippet.firstLine}–{snippet.lastLine}
      </div>
      <pre style={{ margin: 0, padding: '16px 20px', fontSize: 19, lineHeight: 1.5, whiteSpace: 'pre-wrap', color: t.ink, minHeight: snippet.rows.length * 28.5 }}>
        {snippet.rows.map((row, i) => {
          const line = row.map((tok, j) => {
            const shown = tok.content.slice(0, Math.max(0, left));
            left -= tok.content.length;
            return <span key={j} style={{ color: tok.color }}>{shown}</span>;
          });
          left -= 1;
          return <div key={i}>{line}</div>;
        })}
      </pre>
    </div>
  );
};
