import { mono, t } from '../theme.js';

// Burned-in caption; the same text goes to the .vtt track.
export const Caption = ({ text }) => (
  <div style={{ position: 'absolute', left: 0, right: 0, bottom: 56, display: 'flex', justifyContent: 'center' }}>
    <div style={{ maxWidth: 1400, background: t.paper, color: t.ink, fontFamily: mono, fontSize: 38, lineHeight: 1.35,
      padding: '18px 28px', border: `2px solid ${t.ink}`, boxShadow: t.shadow, borderRadius: 2 }}>{text}</div>
  </div>
);
