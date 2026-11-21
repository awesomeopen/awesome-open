import { Composition } from 'remotion';
import videos from './generated/videos.json';
import { footageSeconds, Video } from './Video.jsx';
import { loadFonts } from './theme.js';

loadFonts();

// One composition per prepared video (scripts/prepare.mjs writes videos.json): the
// opening card, the footage and the closing card.
export const Root = () => Object.entries(videos).map(([id, bundle]) => {
  const { fps, width, height } = bundle.beats;
  const { intro, outro } = bundle.cards || { intro: 0, outro: 0 };
  const seconds = intro + footageSeconds(bundle) + outro;
  return <Composition key={id} id={id} component={Video} defaultProps={{ id }}
    durationInFrames={Math.round(seconds * fps)} fps={fps} width={width} height={height} />;
});
