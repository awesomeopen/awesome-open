import { v } from '../theme.js';

// A persistent statement in the video layer, such as a disclosure or credit.
export const Note = ({ overlay }) => {
  // An end card: several lines, centred, larger.
  if (overlay.lines) return (
    <div style={{ position: 'absolute', left: 0, right: 0, top: overlay.top || 300, display: 'flex', justifyContent: 'center' }}>
      <div style={{ maxWidth: 1300, background: v.chip, color: v.text, fontFamily: v.sans, padding: '28px 40px', borderRadius: 8 }}>
        {overlay.lines.map((line, i) => <div key={i} style={{ fontSize: i ? 32 : 40, fontWeight: i ? 400 : 700, color: i === overlay.lines.length - 1 && overlay.source ? v.dim : v.text, marginTop: i ? 12 : 0 }}>{line}</div>)}
      </div>
    </div>
  );
  const [x, y] = overlay.at || [32, 28];
  return (
    <div style={{ position: 'absolute', left: x, top: y, background: v.chip, color: v.text, fontFamily: v.sans, fontSize: 24,
      padding: '6px 14px', borderRadius: 6 }}>{overlay.text}</div>
  );
};
