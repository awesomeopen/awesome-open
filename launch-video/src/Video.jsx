import { AbsoluteFill, OffthreadVideo, Sequence, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import videos from './generated/videos.json';
import { Camera } from './components/Camera.jsx';
import { Card } from './components/Card.jsx';
import { placeBoxes, Stage } from './components/Stage.jsx';
import { Caption } from './components/Caption.jsx';
import { Claims } from './components/Claims.jsx';
import { Draw } from './components/Draw.jsx';
import { Highlight } from './components/Highlight.jsx';
import { Note } from './components/Note.jsx';
import { Transcript } from './components/Transcript.jsx';
import { Clock } from './components/Clock.jsx';
import { CodePanel } from './components/CodePanel.jsx';
import { ValueCheck } from './components/ValueCheck.jsx';
import { t } from './theme.js';

const active = (item, s) => s >= item.from && s < item.to;
export const footageSeconds = bundle => bundle.segments.reduce((sum, seg) => sum + seg.length, 0);

// The footage with its video layer; output seconds start at 0 after the opening card.
const Footage = ({ bundle }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = frame / fps;
  const seg = bundle.segments.find(x => s >= x.start && s < x.start + x.length) || bundle.segments.at(-1);
  // Capture seconds drive the camera and the real-time clock.
  const captureTime = seg.in + (s - seg.start) * seg.speed;
  // A segment that does not start where the previous one ended is a cut; name it
  // for 2.5 s.
  const index = bundle.segments.indexOf(seg);
  const previous = bundle.segments[index - 1];
  const cut = previous && (previous.take !== seg.take || previous.out !== seg.in) && s - seg.start < 2.5
    ? { from: previous.out, to: seg.in, note: seg.cutNote, take: previous.take !== seg.take ? seg.take : null } : null;
  const visible = bundle.beats.boxes
    ? placeBoxes({ boxes: bundle.beats.boxes, regions: bundle.events.regions, s, captureTime, take: seg.take }) : [];
  let snippet = 0;
  return (
    <AbsoluteFill style={{ background: t.paper }}>
      {bundle.beats.boxes
        ? <Stage visible={visible} segments={bundle.segments} masks={bundle.events.masks} maskColor={bundle.events.maskColor}
          captureTime={captureTime} take={seg.take} />
        : <Camera keyframes={bundle.events.keyframes} size={bundle.session.size} time={captureTime}>
          {bundle.segments.map(x => (
            <Sequence key={x.file} from={Math.round(x.start * fps)} durationInFrames={Math.round(x.length * fps)}>
              <OffthreadVideo src={staticFile(x.file)} playbackRate={x.speed} muted />
            </Sequence>
          ))}
        </Camera>}
      {bundle.beats.overlays.map((o, i) => {
        if (o.type === 'code') { const data = bundle.snippets[snippet++]; return active(o, s) && <CodePanel key={i} overlay={o} snippet={data} s={s} />; }
        if (!active(o, s)) return null;
        if (o.type === 'clock') return <Clock key={i} captureTime={captureTime} speed={seg.speed} cut={cut} />;
        if (o.type === 'draw') return <Draw key={i} overlay={o} draw={bundle.draw} s={s} />;
        if (o.type === 'transcript') return <Transcript key={i} overlay={o} s={s} />;
        if (o.type === 'note') return <Note key={i} overlay={o} />;
        if (o.type === 'claims') return <Claims key={i} overlay={o} facts={bundle.facts} s={s} />;
        if (o.type === 'valueCheck') return <ValueCheck key={i} overlay={o} facts={bundle.facts} s={s} />;
        if (o.type === 'highlight') return <Highlight key={i} overlay={o} visible={visible} s={s} />;
        throw new Error('Unknown overlay ' + o.type);
      })}
      {bundle.beats.beats.filter(b => active(b, s)).map(b => <Caption key={b.from} text={b.caption} />)}
    </AbsoluteFill>
  );
};

export const Video = ({ id }) => {
  const bundle = videos[id];
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = frame / fps;
  const { intro, outro } = bundle.cards || { intro: 0, outro: 0 };
  const footage = footageSeconds(bundle);
  const end = intro + footage;
  return (
    <AbsoluteFill style={{ background: '#000' }}>
      {intro > 0 && s < intro && <Card image={bundle.images.intro} card={bundle.beats.intro} s={s} marks />}
      <Sequence from={Math.round(intro * fps)} durationInFrames={Math.round(footage * fps)}>
        <Footage bundle={bundle} />
      </Sequence>
      {outro > 0 && s >= end && <Card image={bundle.images.outro} card={bundle.beats.outro} s={s}
        fadeFrom={end + outro - 1} fadeTo={end + outro} />}
    </AbsoluteFill>
  );
};
