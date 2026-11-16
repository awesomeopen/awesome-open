// Stage 7: automated checks on the render, written to 07-qc.md for gate 2.
// FAIL exits non-zero; WARN needs a reviewer's look.
//   node scripts/qc.mjs <video>
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { REPO, logStage, probe, readJson, run, sha256, sha256File, timeline, videoDir } from './lib.mjs';

const id = process.argv[2];
const dir = videoDir(id);
const beats = readJson(join(dir, '02-beats.json'));
const out = join(dir, '06-render/out.mp4');
if (!existsSync(out)) throw new Error(`Run: node scripts/render.mjs ${id}`);
const results = [];
const check = (status, name, detail) => results.push({ status, name, detail });

// Length and format.
const info = probe(out);
const expected = Math.round(timeline(beats.segments).reduce((n, seg) => n + seg.length, 0) * beats.fps);
const frames = Number(info.nb_read_packets);
check(frames === expected ? 'PASS' : 'FAIL', 'Frame count', `${frames} of ${expected} expected`);
check(info.width === beats.width && info.height === beats.height ? 'PASS' : 'FAIL', 'Size', `${info.width}×${info.height}`);

// Blank and frozen stretches. Screen captures hold still often, so a freeze is a WARN.
const errLog = execFileSync('sh', ['-c', `ffmpeg -hide_banner -i "${out}" -vf "blackdetect=d=0.2:pix_th=0.1,freezedetect=n=0.001:d=2" -an -f null - 2>&1 || true`], { encoding: 'utf8' });
const blacks = (errLog.match(/black_start/g) || []).length;
const freezes = [...errLog.matchAll(/freeze_start: ([\d.]+)/g)].map(m => Number(m[1]).toFixed(1));
check(blacks ? 'FAIL' : 'PASS', 'Blank frames', blacks ? `${blacks} stretch(es)` : 'none');
check(freezes.length ? 'WARN' : 'PASS', 'Frozen ≥ 2 s', freezes.length ? 'from ' + freezes.join(', ') + ' s' : 'none');

// Captions: on screen long enough to read (≤ 17 characters per second, ≥ 1.5 s).
for (const b of beats.beats) {
  const seconds = b.to - b.from, rate = b.caption.length / seconds;
  const ok = rate <= 17 && seconds >= 1.5;
  check(ok ? 'PASS' : 'FAIL', `Caption at ${b.from} s`, `${b.caption.length} chars in ${seconds} s (${rate.toFixed(1)}/s)`);
}

// Values: every overlay field comes from 05-facts.json, which records its catalog.
const facts = existsSync(join(dir, '05-facts.json')) ? readJson(join(dir, '05-facts.json')) : null;
for (const o of beats.overlays.filter(x => x.type === 'valueCheck')) {
  for (const name of o.projects) for (const field of o.fields) {
    const f = facts?.projects[name]?.fields[field];
    check(f ? 'PASS' : 'FAIL', `Value ${name} · ${field}`, f ? `${f.value ?? 'Unknown'} (${f.source}, observed ${f.observed ?? 'n/a'})` : 'missing from 05-facts.json');
  }
}
for (const c of facts?.claims || []) {
  const ok = c.source !== 'catalog' || c.verified;
  check(ok ? 'PASS' : 'FAIL', `Claim (${c.source})`, `${c.text}${c.source === 'catalog' ? ` · found in ${c.project}'s record` : ' · ' + c.detail}`);
}
for (const [file, hash] of Object.entries(facts?.lists || {})) check('PASS', 'Facts source', `${file}, sha256 ${hash.slice(0, 12)}`);
if (facts?.catalog) check('PASS', 'Facts source', `${facts.catalog.source}, fetched ${facts.catalog.fetched_at}, sha256 ${facts.catalog.sha256.slice(0, 12)}`);

// Code: the snippet on screen still matches the repository file it was read from.
const bundle = readJson(join(dir, '../../src/generated/videos.json'))[id];
for (const s of bundle.snippets) {
  const now = sha256(readFileSync(join(REPO, s.file), 'utf8'));
  check(now === s.fileSha ? 'PASS' : 'FAIL', `Code ${s.file}:${s.firstLine}`, now === s.fileSha ? 'matches the repository' : 'file changed since render');
}

// Contact sheet: one frame per second.
const sheet = join(dir, '06-render/contact.jpg');
run('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-i', out, '-vf', 'fps=1,scale=480:-2,tile=5x2', '-frames:v', '1', sheet]);

const failed = results.filter(r => r.status === 'FAIL').length;
const lines = ['# QC: ' + id, '', `Render: \`06-render/out.mp4\` (sha256 ${sha256File(out).slice(0, 12)}), checked ${new Date().toISOString()}.`,
  'Contact sheet: `06-render/contact.jpg` (git-ignored).', '', '| Result | Check | Detail |', '| --- | --- | --- |',
  ...results.map(r => `| ${r.status} | ${r.name} | ${r.detail} |`), '', 'Gate decisions: `approvals.md`.', ''];
writeFileSync(join(dir, '07-qc.md'), lines.join('\n'));
logStage(dir, 'qc', { out: sha256File(out) });
console.log(`07-qc.md: ${results.length - failed} passed or warned, ${failed} failed`);
process.exit(failed ? 1 : 0);
