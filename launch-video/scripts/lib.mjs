// Shared helpers for the stage scripts. Every stage reads files from earlier stages
// and writes its own; production.log records each run with its input hashes.
import { createHash } from 'node:crypto';
import { appendFileSync, existsSync, readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export const REPO = resolve(ROOT, '..');

export function videoDir(id) {
  if (!id || !/^[a-z0-9-]+$/.test(id)) throw new Error('Usage: <stage> <video id>, e.g. test or v1');
  const dir = join(ROOT, 'videos', id);
  if (!existsSync(dir)) throw new Error(`No such video: ${dir}`);
  return dir;
}

export const readJson = file => JSON.parse(readFileSync(file, 'utf8'));
export const sha256 = data => createHash('sha256').update(data).digest('hex');
export const sha256File = file => sha256(readFileSync(file));

export function gitRevision() {
  const rev = execFileSync('git', ['-C', REPO, 'rev-parse', '--short', 'HEAD'], { encoding: 'utf8' }).trim();
  const dirty = execFileSync('git', ['-C', REPO, 'status', '--porcelain'], { encoding: 'utf8' }).trim();
  return dirty ? rev + '+dirty' : rev;
}

// One line per stage run: UTC time, stage, repository revision, then input=hash pairs.
export function logStage(dir, stage, inputs) {
  const hashes = Object.entries(inputs).map(([name, hash]) => `${name}=${hash.slice(0, 12)}`).join(' ');
  appendFileSync(join(dir, 'production.log'), `${new Date().toISOString()} ${stage} repo=${gitRevision()} ${hashes}\n`);
}

export function run(cmd, args) {
  execFileSync(cmd, args, { stdio: ['ignore', 'inherit', 'inherit'] });
}

export function probe(file) {
  const out = execFileSync('ffprobe', ['-v', 'error', '-count_packets', '-select_streams', 'v:0',
    '-show_entries', 'stream=width,height,nb_read_packets,r_frame_rate,color_transfer:format=duration',
    '-of', 'json', file], { encoding: 'utf8' });
  const data = JSON.parse(out);
  return { ...data.streams[0], duration: Number(data.format.duration) };
}

// Output seconds for each capture segment; the clock and speed tags use the same map.
export function timeline(segments) {
  let at = 0;
  return segments.map(seg => {
    const length = (seg.out - seg.in) / seg.speed;
    const entry = { ...seg, start: at, length };
    at += length;
    return entry;
  });
}
