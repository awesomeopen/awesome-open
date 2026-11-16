import { Easing, interpolate, useVideoConfig } from 'remotion';

// Fits the capture rect for the current capture second into the frame, easing
// between hand-marked or logged keyframes (04-capture/events.json).
export const Camera = ({ keyframes, size: [w, h], time, children }) => {
  const { width, height } = useVideoConfig();
  const times = keyframes.map(k => k.t);
  const ease = { easing: Easing.inOut(Easing.cubic), extrapolateLeft: 'clamp', extrapolateRight: 'clamp' };
  const [x, y, rw, rh] = [0, 1, 2, 3].map(i => times.length > 1
    ? interpolate(time, times, keyframes.map(k => k.rect[i]), ease)
    : keyframes[0].rect[i]);
  const scale = Math.min(width / rw, height / rh);
  const tx = width / 2 - (x + rw / 2) * scale;
  const ty = height / 2 - (y + rh / 2) * scale;
  return (
    <div style={{ position: 'absolute', width: w, height: h, transformOrigin: '0 0',
      transform: `translate(${tx}px, ${ty}px) scale(${scale})` }}>{children}</div>
  );
};
