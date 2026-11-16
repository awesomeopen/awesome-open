import { mono, t } from '../theme.js';

// Real time in the capture, and the playback speed whenever it is not 1×.
export const Clock = ({ captureTime, speed }) => {
  const m = Math.floor(captureTime / 60), sec = Math.floor(captureTime % 60);
  return (
    <div style={{ position: 'absolute', top: 36, right: 40, display: 'flex', gap: 12, fontFamily: mono, fontSize: 24 }}>
      {speed !== 1 && <span style={{ background: t.scarlet, color: t.paper, padding: '6px 12px' }}>{speed}× speed</span>}
      <span style={{ background: t.blueprint, color: t.paper, padding: '6px 12px' }}>
        Real time {m}:{String(sec).padStart(2, '0')}
      </span>
    </div>
  );
};
