import { interpolate } from 'remotion';
import { mono, t } from '../theme.js';

// What the client said, each with where it came from. The source is written out,
// so the state never depends on colour alone.
const TAG = { catalog: 'Catalog', web: 'Web', generated: 'Generated' };

export const Claims = ({ overlay, facts, s }) => {
  const step = (overlay.to - overlay.from) / (facts.claims.length + 1);
  return (
    <div style={{ position: 'absolute', left: 48, top: 120, width: 760, display: 'flex', flexDirection: 'column', gap: 16 }}>
      {facts.claims.map((c, i) => {
        const opacity = interpolate(s, [overlay.from + i * step, overlay.from + i * step + 0.4], [0, 1],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
        return (
          <div key={i} style={{ opacity, background: t.paper, border: `2px solid ${t.ink}`, boxShadow: t.shadow, fontFamily: mono, padding: '12px 18px' }}>
            <div style={{ fontSize: 22, color: c.source === 'generated' ? t.muted : t.blueprint }}>
              {TAG[c.source]}{c.observed ? ' · checked ' + c.observed : ''}
            </div>
            <div style={{ fontSize: 30, color: t.ink, lineHeight: 1.3 }}>{c.text}</div>
            <div style={{ fontSize: 20, color: t.muted }}>{c.detail}</div>
          </div>
        );
      })}
    </div>
  );
};
