// Stage 6b: prepare, then render the master, poster and caption track.
//   node scripts/render.mjs <video>
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { ROOT, cards, logStage, readJson, run, sha256File, videoDir } from './lib.mjs';

const id = process.argv[2];
const dir = videoDir(id);
run('node', [join(ROOT, 'scripts/prepare.mjs'), id]);
const beats = readJson(join(dir, '02-beats.json'));
const out = join(dir, '06-render');
mkdirSync(out, { recursive: true });
const remotion = join(ROOT, 'node_modules/.bin/remotion');
const entry = join(ROOT, 'src/index.js');
run(remotion, ['render', entry, id, join(out, 'out.mp4'), '--codec', 'h264', '--crf', '18', '--log', 'error']);
// The poster is the opening card when there is one, else the first beat's midpoint.
const { intro } = cards(beats);
const poster = intro ? 0 : Math.round(((beats.beats[0].from + beats.beats[0].to) / 2) * beats.fps);
run(remotion, ['still', entry, id, join(out, 'poster.png'), '--frame', String(poster), '--log', 'error']);

const stamp = s => new Date(s * 1000).toISOString().slice(11, 23);
writeFileSync(join(out, 'captions.vtt'), 'WEBVTT\n\n' + beats.beats.map(b => `${stamp(intro + b.from)} --> ${stamp(intro + b.to)}\n${b.caption}\n`).join('\n'));
logStage(dir, 'render', { out: sha256File(join(out, 'out.mp4')) });
console.log('Rendered ' + join(out, 'out.mp4'));
