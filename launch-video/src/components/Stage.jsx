import { Easing, interpolate, OffthreadVideo, Sequence, staticFile, useVideoConfig } from 'remotion';
import { v } from '../theme.js';

// A neutral stage holding labelled boxes, each a region of the capture. A box with a
// parent lifts out of the spot where its region sits in the parent and returns
// there when it leaves, so the viewer sees where each view comes from.
const MOVE = 0.9;
const ease = Easing.inOut(Easing.cubic);
const mix = (a, b, p) => a.map((x, i) => x + (b[i] - x) * ease(Math.min(1, Math.max(0, p))));

// Capture rect of a named region at a capture second (the latest keyframe at or before it).
// Keyframes may name a take; those without one apply to every take.
export const regionAt = (regions, name, time, take) => {
  const list = (regions[name] || []).filter(k => !k.take || k.take === take);
  if (!list.length) throw new Error('Unknown region ' + name + (take ? ' in take ' + take : ''));
  return (list.filter(k => k.t <= time).at(-1) || list[0]).rect;
};

// Screen rect [x, y, w, h] of a box's layout at output second s, before entering or leaving.
const layoutAt = (box, s, region) => {
  const keys = box.at;
  const k = keys.filter(x => x.t <= s).at(-1) || keys[0];
  const prev = keys[keys.indexOf(k) - 1];
  const [cx, cy, w] = prev && s < k.t + MOVE ? mix(prev.rect, k.rect, (s - k.t) / MOVE) : k.rect;
  const h = w * region[3] / region[2];
  return [cx - w / 2, cy - h / 2, w, h];
};

export const Stage = ({ boxes, regions, segments, s, captureTime, take }) => {
  const { fps } = useVideoConfig();
  const placed = {};
  const visible = [];
  for (const box of boxes) {
    if (s < box.from || s >= box.to) continue;
    const region = regionAt(regions, box.region, captureTime, take);
    let rect = layoutAt(box, s, region);
    let opacity = 1;
    const parent = box.parent && placed[box.parent];
    const into = Math.min((s - box.from) / MOVE, (box.to - s) / MOVE);
    if (into < 1) {
      if (parent) {
        // Where this region sits inside the parent box right now.
        const scale = parent.rect[2] / parent.region[2];
        const from = [parent.rect[0] + (region[0] - parent.region[0]) * scale, parent.rect[1] + (region[1] - parent.region[1]) * scale,
          region[2] * scale, region[3] * scale];
        rect = mix(from, rect, into);
      } else {
        opacity = Math.max(0, into);
      }
    }
    placed[box.id] = { rect, region };
    visible.push({ box, rect, region, opacity });
  }
  return (
    <div style={{ position: 'absolute', inset: 0, background: v.stage }}>
      {visible.map(({ box, rect: [x, y, w, h], region, opacity }) => {
        const scale = w / region[2];
        const site = box.kind === 'site';
        return (
          <div key={box.id} style={{ position: 'absolute', left: x, top: y, width: w, height: h, opacity }}>
            <div style={{ position: 'absolute', left: 0, bottom: h + 10, whiteSpace: 'nowrap', fontFamily: v.sans, fontSize: 24,
              color: v.text, background: v.chip, padding: '5px 12px', borderRadius: 6 }}>{box.label}</div>
            <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', borderRadius: 6,
              outline: `${site ? 4 : 2}px solid ${site ? v.edgeSite : v.edgeOther}`, boxShadow: '0 24px 60px rgba(0,0,0,0.55)' }}>
              {segments.map(seg => (
                <Sequence key={seg.file} from={Math.round(seg.start * fps)} durationInFrames={Math.round(seg.length * fps)} layout="none">
                  <OffthreadVideo src={staticFile(seg.file)} playbackRate={seg.speed} muted
                    style={{ position: 'absolute', left: -region[0] * scale, top: -region[1] * scale, width: seg.size[0] * scale, height: seg.size[1] * scale, maxWidth: 'none' }} />
                </Sequence>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
};
