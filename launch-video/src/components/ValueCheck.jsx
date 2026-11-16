import { interpolate } from 'remotion';
import { display, mono, t } from '../theme.js';

// Each value the client states, beside the catalog's record and its observation
// date. The source tag is text, so the state never depends on colour alone.
const TAG = { catalog: 'Catalog', web: 'Web', generated: 'Generated' };

export const ValueCheck = ({ overlay, facts, s }) => {
  const opacity = interpolate(s, [overlay.from, overlay.from + 0.4], [0, 1], { extrapolateRight: 'clamp' });
  return (
    <div style={{ position: 'absolute', left: (overlay.at || [48])[0], top: (overlay.at || [48, 120])[1], display: 'flex',
      flexDirection: overlay.direction || 'row', gap: 24, opacity }}>
      {overlay.projects.map(name => {
        const project = facts.projects[name];
        return (
          <div key={name} style={{ width: 520, background: t.paper, border: `2px solid ${t.ink}`, boxShadow: t.shadow }}>
            <div style={{ fontFamily: display, fontSize: 40, color: t.blueprint, padding: '14px 20px 6px' }}>{name}</div>
            {overlay.fields.map(field => {
              const f = project.fields[field];
              const unknown = f.value === null;
              return (
                <div key={field} style={{ fontFamily: mono, padding: '10px 20px', borderTop: `1px solid ${t.trace}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 20, color: t.muted }}>
                    <span>{f.label}</span>
                    <span>{TAG[f.source]}{f.observed ? ' · ' + f.observed.slice(0, 10) : ''}</span>
                  </div>
                  <div style={{ fontSize: 34, color: unknown ? t.muted : t.ink }}>
                    {unknown ? 'Unknown' : typeof f.value === 'number' ? f.value.toLocaleString('en-US') : f.value}
                  </div>
                </div>
              );
            })}
          </div>
        );
      })}
    </div>
  );
};
