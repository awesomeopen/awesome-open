import { interpolate } from 'remotion';
import { v } from '../theme.js';

// The V2 draw from 00-draw.json: the screened pool, the seed and the pick. The
// highlight steps through the pool and settles on the drawn list.
export const Draw = ({ overlay, draw, s }) => {
  const settle = overlay.from + (overlay.to - overlay.from) * 0.55;
  const steps = Math.floor(interpolate(s, [overlay.from, settle], [0, draw.pool.length * 2 + draw.index], { extrapolateRight: 'clamp' }));
  const lit = s < settle ? steps % draw.pool.length : draw.index;
  const [x, y, w] = overlay.at || [1080, 160, 760];
  return (
    <div style={{ position: 'absolute', left: x, top: y, width: w, background: v.chip, color: v.text, fontFamily: v.sans, padding: '20px 26px', borderRadius: 6 }}>
      <div style={{ fontSize: 22, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase' }}>Draw · {draw.date}</div>
      <div style={{ fontSize: 21, color: v.dim, margin: '6px 0 14px' }}>From the {draw.pool.length} lists that passed screening. Seed {draw.seed.slice(0, 12)}…</div>
      {draw.pool.map((repo, i) => (
        <div key={repo} style={{ fontSize: 30, padding: '6px 12px', borderRadius: 4, background: i === lit ? v.text : 'transparent', color: i === lit ? '#000' : v.text }}>
          {i === lit && s >= settle ? '▶ ' : ''}{repo}
        </div>
      ))}
      {s >= settle && <div style={{ fontSize: 24, marginTop: 14 }}>
        {draw.drawn.licence} · revision {draw.drawn.revision.slice(0, 7)} · question: {draw.drawn.ask}
      </div>}
    </div>
  );
};
