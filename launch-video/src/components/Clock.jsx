import { mono, t } from '../theme.js';

const time = s => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

// Real time in the capture, the playback speed whenever it is not 1×, and for the
// first seconds after a cut, what was left out.
export const Clock = ({ captureTime, speed, cut }) => (
  <div style={{ position: 'absolute', top: 36, right: 40, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 8, fontFamily: mono, fontSize: 24 }}>
    <div style={{ display: 'flex', gap: 12 }}>
      {speed !== 1 && <span style={{ background: t.scarlet, color: t.paper, padding: '6px 12px' }}>{speed}× speed</span>}
      <span style={{ background: t.blueprint, color: t.paper, padding: '6px 12px' }}>Real time {time(captureTime)}</span>
    </div>
    {cut && <span style={{ background: t.paper, color: t.ink, border: `2px solid ${t.ink}`, padding: '6px 12px' }}>
      Cut {time(cut.from)}–{time(cut.to)}: {cut.note}</span>}
  </div>
);
