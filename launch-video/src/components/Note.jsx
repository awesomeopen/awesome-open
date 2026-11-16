import { v } from '../theme.js';

// A persistent statement in the video layer, such as a disclosure or credit.
export const Note = ({ overlay }) => {
  const [x, y] = overlay.at || [32, 28];
  return (
    <div style={{ position: 'absolute', left: x, top: y, background: v.chip, color: v.text, fontFamily: v.sans, fontSize: 24,
      padding: '6px 14px', borderRadius: 6 }}>{overlay.text}</div>
  );
};
