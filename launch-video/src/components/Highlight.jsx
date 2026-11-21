import { Easing, interpolate } from 'remotion';
import { v } from '../theme.js';

// Where to look: a numbered marker on one spot of a box (rect in capture pixels,
// following the box as it moves) or of the screen (`at`, output pixels). Three per
// video, numbered 1 to 3. "frame" rings the spot; "underline" draws a bar under it.
const PAD = 10;
const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' };

export const Highlight = ({ overlay, visible, s }) => {
  let rect = overlay.at;
  // `badge` places the number's centre elsewhere when the spot left of the target holds text.
  let centre = overlay.badge;
  if (overlay.box) {
    const placed = visible.find(x => x.box.id === overlay.box);
    if (!placed) return null;
    const [bx, by, bw] = placed.rect;
    const scale = bw / placed.region[2];
    const map = ([px, py]) => [bx + (px - placed.region[0]) * scale, by + (py - placed.region[1]) * scale];
    const [x, y, w, h] = overlay.rect;
    rect = [...map([x, y]), w * scale, h * scale];
    if (centre) centre = map(centre);
  }
  const [x, y, w, h] = rect;
  const [cx, cy] = centre || [x - PAD - 36, y + h / 2];
  const grow = interpolate(s, [overlay.from, overlay.from + 0.35], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  const opacity = interpolate(s, [overlay.to - 0.3, overlay.to], [1, 0], clamp);
  const badge = (
    <div style={{ position: 'absolute', left: cx - 26, top: cy - 26, width: 52, height: 52, borderRadius: 26,
      background: v.mark, color: v.text, fontFamily: v.sans, fontSize: 32, fontWeight: 700, display: 'flex',
      alignItems: 'center', justifyContent: 'center', transform: `scale(${grow})`, boxShadow: '0 4px 14px rgba(0,0,0,0.45)' }}>{overlay.n}</div>
  );
  return (
    <div style={{ position: 'absolute', inset: 0, opacity, pointerEvents: 'none' }}>
      {overlay.style === 'underline'
        ? <div style={{ position: 'absolute', left: x, top: y + h + 2, width: w, height: 10, borderRadius: 5, background: v.mark,
          transformOrigin: '0 50%', transform: `scaleX(${grow})`, boxShadow: '0 2px 8px rgba(0,0,0,0.35)' }} />
        : <div style={{ position: 'absolute', left: x - PAD, top: y - PAD, width: w + 2 * PAD, height: h + 2 * PAD, borderRadius: 10,
          border: `6px solid ${v.mark}`, opacity: grow, transform: `scale(${1.08 - 0.08 * grow})`, boxShadow: '0 0 0 2px rgba(0,0,0,0.25)' }} />}
      {badge}
    </div>
  );
};
