import { interpolate } from 'remotion';
import { v } from '../theme.js';

// Tool calls and results transcribed from the session record, for steps the
// footage shows only as "Ran 1 shell command". Labelled as transcribed.
export const Transcript = ({ overlay, s }) => {
  const step = (overlay.to - overlay.from) / (overlay.items.length + 0.5);
  const [x, y, w] = overlay.at || [80, 150, 780];
  return (
    <div style={{ position: 'absolute', left: x, top: y, width: w, background: v.chip, color: v.text, fontFamily: v.sans, padding: '18px 24px', borderRadius: 6 }}>
      <div style={{ fontSize: 22, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase' }}>{overlay.title}</div>
      <div style={{ fontSize: 20, color: v.dim, marginBottom: 10 }}>{overlay.source}</div>
      {overlay.items.map((item, i) => {
        const opacity = interpolate(s, [overlay.from + i * step, overlay.from + i * step + 0.4], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
        return (
          <div key={i} style={{ opacity, marginTop: 12 }}>
            <div style={{ fontFamily: "'Commit Mono', ui-monospace, monospace", fontSize: 24 }}>{item.call}</div>
            <div style={{ fontSize: 24, color: v.dim, marginTop: 2 }}>→ {item.result}</div>
          </div>
        );
      })}
    </div>
  );
};
