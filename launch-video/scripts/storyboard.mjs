// Stage 3: one still per beat at its midpoint, plus a contact sheet for gate 1.
//   node scripts/storyboard.mjs <video>
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { ROOT, logStage, readJson, run, sha256File, videoDir } from './lib.mjs';

const id = process.argv[2];
const dir = videoDir(id);
run('node', [join(ROOT, 'scripts/prepare.mjs'), id]);
const beats = readJson(join(dir, '02-beats.json'));
const out = join(dir, '03-storyboard');
mkdirSync(out, { recursive: true });
const remotion = join(ROOT, 'node_modules/.bin/remotion');
beats.beats.forEach((b, i) => {
  const frame = Math.round(((b.from + b.to) / 2) * beats.fps);
  run(remotion, ['still', join(ROOT, 'src/index.js'), id, join(out, `beat-${String(i + 1).padStart(2, '0')}.png`), '--frame', String(frame), '--log', 'error']);
});
const cols = Math.min(3, beats.beats.length), rows = Math.ceil(beats.beats.length / cols);
run('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-pattern_type', 'glob', '-i', join(out, 'beat-*.png'),
  '-vf', `scale=640:-2,pad=iw+8:ih+8:4:4:white,tile=${cols}x${rows}`, '-frames:v', '1', join(out, 'contact.jpg')]);
logStage(dir, 'storyboard', { beats: sha256File(join(dir, '02-beats.json')) });
console.log('Storyboard ' + join(out, 'contact.jpg'));
