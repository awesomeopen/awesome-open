import { v } from '../theme.js';

// Burned-in caption in the video's neutral layer; the same text goes to the .vtt track.
export const Caption = ({ text }) => (
  <div style={{ position: 'absolute', left: 0, right: 0, bottom: 40, display: 'flex', justifyContent: 'center' }}>
    <div style={{ maxWidth: 1500, background: v.chip, color: v.text, fontFamily: v.sans, fontSize: 40, fontWeight: 500,
      lineHeight: 1.3, padding: '14px 26px', borderRadius: 6 }}>{text}</div>
  </div>
);
