import { v } from '../theme.js';

const time = s => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
const chip = { background: v.chip, color: v.text, padding: '6px 14px', borderRadius: 6 };

// Real time in the capture; the playback speed whenever it is not 1×; and for the
// first seconds after a cut, what was left out.
export const Clock = ({ captureTime, speed, cut }) => (
  <div style={{ position: 'absolute', top: 28, right: 32, display: 'flex', flexDirection: 'column', alignItems: 'flex-end',
    gap: 8, fontFamily: v.sans, fontSize: 24 }}>
    <div style={{ display: 'flex', gap: 10 }}>
      {speed !== 1 && <span style={chip}>{speed}× speed</span>}
      <span style={chip}>Real time {time(captureTime)}</span>
    </div>
    {cut && <span style={chip}>{cut.take ? `Take ${cut.take}: ${cut.note}` : `Cut ${time(cut.from)}–${time(cut.to)}: ${cut.note}`}</span>}
  </div>
);
