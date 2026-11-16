import { Composition } from 'remotion';
import videos from './generated/videos.json';
import { Video } from './Video.jsx';
import { loadFonts } from './theme.js';

loadFonts();

// One composition per prepared video (scripts/prepare.mjs writes videos.json).
export const Root = () => Object.entries(videos).map(([id, bundle]) => {
  const { fps, width, height } = bundle.beats;
  const seconds = bundle.segments.reduce((sum, seg) => sum + seg.length, 0);
  return <Composition key={id} id={id} component={Video} defaultProps={{ id }}
    durationInFrames={Math.round(seconds * fps)} fps={fps} width={width} height={height} />;
});
