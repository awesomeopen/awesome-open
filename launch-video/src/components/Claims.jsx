import { interpolate } from 'remotion';
import { v } from '../theme.js';

// What the client said, each with where it came from, in the video's neutral layer.
// The source is written out, so the state never depends on colour alone.
const TAG = { catalog: 'Catalog', web: 'Web', generated: 'Generated' };

export const Claims = ({ overlay, facts, s }) => {
  const step = (overlay.to - overlay.from) / (facts.claims.length + 1);
  const [x, y, w] = overlay.at || [48, 120, 760];
  return (
    <div style={{ position: 'absolute', left: x, top: y, width: w, display: 'flex', flexDirection: 'column', gap: 14 }}>
      {facts.claims.map((c, i) => {
        const opacity = interpolate(s, [overlay.from + i * step, overlay.from + i * step + 0.4], [0, 1],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
        return (
          <div key={i} style={{ opacity, background: v.chip, color: v.text, fontFamily: v.sans, padding: '14px 20px', borderRadius: 6 }}>
            <div style={{ fontSize: 22, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase' }}>
              {TAG[c.source]}{c.observed ? ' · checked ' + c.observed : ''}
            </div>
            <div style={{ fontSize: 30, lineHeight: 1.3, marginTop: 4 }}>{c.text}</div>
            <div style={{ fontSize: 21, color: v.dim, marginTop: 4 }}>{c.detail}</div>
          </div>
        );
      })}
    </div>
  );
};
