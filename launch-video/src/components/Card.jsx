import { AbsoluteFill, Img, interpolate, staticFile } from 'remotion';
import { v } from '../theme.js';

// Opening and closing cards: a full-frame image with left-aligned text. On the
// opening card the eyebrow starts at half height, with the title and subtitle below;
// the closing card's text is centred vertically. The opening card carries the list
// mark (the Awesome Open* fruit, or the card's `mark`) and the Jumper MCP mouse side
// by side in the top-right corner, on the image without a backing;
// the dark marks show reversed in white so they read on the night images. The
// closing card has no marks and fades to black.
const MARKS = { fruit: { src: 'brand/fruit.png', height: 64 }, webmcplet: { src: 'brand/webmcplet.png', height: 64, reverse: true } };
const reversed = { filter: 'brightness(0) invert(1) drop-shadow(0 2px 10px rgba(0,0,0,0.5))' };

const Marks = ({ mark }) => {
  const left = MARKS[mark || 'fruit'];
  return (
    <div style={{ position: 'absolute', top: 44, right: 52, display: 'flex', alignItems: 'center', gap: 28 }}>
      <Img src={staticFile(left.src)} style={{ height: left.height,
        ...(left.reverse ? reversed : { filter: 'drop-shadow(0 2px 10px rgba(0,0,0,0.5))' }) }} />
      <Img src={staticFile('brand/jumper.png')} style={{ height: 104, margin: '-14px -10px', ...reversed }} />
    </div>
  );
};

export const Card = ({ image, card, s, fadeFrom, fadeTo, marks }) => {
  const dark = card.text !== 'dark';
  const black = fadeFrom === undefined ? 0 : interpolate(s, [fadeFrom, fadeTo], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  return (
    <AbsoluteFill style={{ background: '#000' }}>
      <Img src={staticFile(image)} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
      {dark && <AbsoluteFill style={{ background: 'linear-gradient(90deg, rgba(0,0,0,0.5) 0%, rgba(0,0,0,0.25) 55%, rgba(0,0,0,0) 85%)' }} />}
      <div style={{ position: 'absolute', left: 120, right: 120, ...(marks ? { top: '50%' } : { top: 0, bottom: 0, justifyContent: 'center' }),
        display: 'flex', flexDirection: 'column', alignItems: 'flex-start', whiteSpace: 'nowrap', fontFamily: v.sans,
        color: dark ? v.text : '#16202B', textShadow: dark ? '0 2px 18px rgba(0,0,0,0.5)' : 'none' }}>
        {card.kicker && <div style={{ fontSize: 30, fontWeight: 600, letterSpacing: 2, textTransform: 'uppercase', opacity: 0.85, lineHeight: 1 }}>{card.kicker}</div>}
        {card.title && <div style={{ fontSize: 76, fontWeight: 700, lineHeight: 1.1, marginTop: card.kicker ? 20 : 0 }}>{card.title}</div>}
        {card.subtitle && <div style={{ fontSize: 38, fontWeight: 400, lineHeight: 1.3, marginTop: 22 }}>{card.subtitle}</div>}
      </div>
      {marks && <Marks mark={card.mark} />}
      <AbsoluteFill style={{ background: '#000', opacity: black }} />
    </AbsoluteFill>
  );
};
