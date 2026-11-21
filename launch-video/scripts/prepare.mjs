// Stage 6a: gather everything a render reads into public/ and src/generated/, from
// the repository and the capture, so the composition never holds copied values.
//   node scripts/prepare.mjs <video>
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { codeToTokens } from 'shiki';
import { REPO, ROOT, cards, logStage, readJson, run, sha256, sha256File, timeline, videoDir } from './lib.mjs';

const id = process.argv[2];
const dir = videoDir(id);
const beats = readJson(join(dir, '02-beats.json'));
const session = readJson(join(dir, '04-capture/session.json'));
const events = readJson(join(dir, '04-capture/events.json'));
const factsFile = join(dir, '05-facts.json');
const needsFacts = beats.overlays.some(o => o.type === 'valueCheck' || o.type === 'claims');
if (needsFacts && !existsSync(factsFile)) throw new Error(`Run: node scripts/facts.mjs ${id}`);
const facts = needsFacts ? readJson(factsFile) : null;

const generated = join(ROOT, 'src/generated');
const pub = join(ROOT, 'public');
mkdirSync(generated, { recursive: true });
mkdirSync(join(pub, 'fonts'), { recursive: true });
mkdirSync(join(pub, id), { recursive: true });

// Brand tokens, read from the site's own token file.
const tokensCss = readFileSync(join(REPO, 'site/design/tokens.css'), 'utf8');
const tokens = Object.fromEntries([...tokensCss.matchAll(/--rs-([a-z0-9-]+):\s*([^;]+);/g)].map(m => [m[1], m[2].trim()]));
for (const [name, value] of Object.entries(tokens)) tokens[name] = value.replace(/var\(--rs-([a-z0-9-]+)\)/g, (_, ref) => tokens[ref]);
writeFileSync(join(generated, 'tokens.json'), JSON.stringify(tokens, null, 2) + '\n');

// Brand fonts, from the site's vendored copies (licences in site/vendor).
const FONTS = { 'commit-mono.woff2': 'site/vendor/commit-mono.woff2', 'poltawski.woff2': 'site/vendor/serif-preview/poltawski.woff2' };
for (const [name, from] of Object.entries(FONTS)) copyFileSync(join(REPO, from), join(pub, 'fonts', name));

// Capture segments, cut from the original recordings and converted to constant
// 30 fps H.264. session.json names one recording, or several under "takes"; a
// segment picks its take by name (default: the first). Each segment starts at time 0,
// so segment time t shows capture second in + t, as the clock says.
const takes = session.takes || { main: session };
const takeShas = {};
for (const [name, take] of Object.entries(takes)) {
  const file = join(REPO, take.source);
  if (!existsSync(file)) throw new Error(`Capture missing for take ${name}: ${take.source}`);
  takeShas[name] = sha256File(file);
  if (takeShas[name] !== take.sha256) throw new Error(`Take ${name}: hash differs from 04-capture/session.json: ${takeShas[name]}`);
}
const segments = timeline(beats.segments).map((seg, i) => {
  const takeName = seg.take || Object.keys(takes)[0];
  const take = takes[takeName];
  if (!take) throw new Error(`Segment ${i} names unknown take ${seg.take}`);
  const file = `${id}/seg-${i}.mp4`;
  const stamp = join(pub, id, `seg-${i}.json`);
  const key = JSON.stringify({ sourceSha: takeShas[takeName], in: seg.in, out: seg.out, zeroStart: true });
  if (!existsSync(stamp) || readFileSync(stamp, 'utf8') !== key) {
    run('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-ss', String(seg.in), '-to', String(seg.out), '-i', join(REPO, take.source),
      '-an', '-vf', 'setpts=PTS-STARTPTS,fps=30,format=yuv420p', '-c:v', 'libx264', '-crf', '14', '-preset', 'medium', join(pub, file)]);
    writeFileSync(stamp, key);
  }
  return { ...seg, take: takeName, file, size: take.size };
});

// Code reveals, read from repository files now, located by their first line.
const theme = {
  name: 'retro-scraperism', type: 'light',
  colors: { 'editor.background': tokens.paper, 'editor.foreground': tokens.ink },
  tokenColors: [
    { scope: ['keyword', 'storage', 'storage.type', 'keyword.operator.new'], settings: { foreground: tokens.blueprint } },
    { scope: ['string', 'string.quoted'], settings: { foreground: tokens.emerald } },
    { scope: ['comment'], settings: { foreground: tokens.muted } },
    { scope: ['entity.name.function', 'support.function'], settings: { foreground: tokens.blueprint } }
  ]
};
const snippets = [];
for (const overlay of beats.overlays.filter(o => o.type === 'code')) {
  const text = readFileSync(join(REPO, overlay.file), 'utf8');
  const lines = text.split('\n');
  const hits = lines.flatMap((line, i) => (line.includes(overlay.start) ? [i] : []));
  if (hits.length !== 1) throw new Error(`${overlay.file}: "${overlay.start}" matches ${hits.length} lines; it must match one`);
  const picked = lines.slice(hits[0], hits[0] + overlay.lines);
  const indent = Math.min(...picked.filter(l => l.trim()).map(l => l.match(/^ */)[0].length));
  const code = picked.map(l => l.slice(indent)).join('\n');
  const { tokens: rows } = await codeToTokens(code, { lang: 'javascript', theme });
  snippets.push({ file: overlay.file, firstLine: hits[0] + 1, lastLine: hits[0] + picked.length, fileSha: sha256(text),
    rows: rows.map(row => row.map(t => ({ content: t.content, color: t.color }))) });
}

// Card images (launch-video/images) and the marks on the opening card.
const images = {};
for (const [name, card] of Object.entries({ intro: beats.intro, outro: beats.outro })) {
  if (!card) continue;
  copyFileSync(join(ROOT, card.image), join(pub, id, `${name}.png`));
  images[name] = `${id}/${name}.png`;
}
if (beats.intro || beats.outro) {
  mkdirSync(join(pub, 'brand'), { recursive: true });
  copyFileSync(join(REPO, 'site/brand/fruit-96.png'), join(pub, 'brand/fruit.png'));
  copyFileSync(join(ROOT, 'images/jumper01_256.png'), join(pub, 'brand/jumper.png'));
  copyFileSync(join(ROOT, 'images/Futuristic WebMCPlet logo lockup.png'), join(pub, 'brand/webmcplet.png'));
}

const drawFile = join(dir, '00-draw.json');
const draw = existsSync(drawFile) ? readJson(drawFile) : null;
const bundle = { beats, session, events, facts, draw, segments, snippets, images, cards: cards(beats), preparedAt: new Date().toISOString() };
const indexFile = join(generated, 'videos.json');
const index = existsSync(indexFile) ? readJson(indexFile) : {};
index[id] = bundle;
writeFileSync(indexFile, JSON.stringify(index, null, 2) + '\n');

logStage(dir, 'prepare', {
  beats: sha256File(join(dir, '02-beats.json')), events: sha256File(join(dir, '04-capture/events.json')),
  ...Object.fromEntries(Object.entries(takeShas).map(([n, h]) => ['take:' + n, h])), ...(facts ? { facts: sha256File(factsFile) } : {}),
  ...Object.fromEntries(snippets.map(s => [s.file + ':' + s.firstLine, s.fileSha])),
  ...Object.fromEntries(Object.keys(images).map(name => ['card:' + name, sha256File(join(pub, images[name]))]))
});
console.log(`Prepared ${id}: ${segments.length} segment(s), ${snippets.length} snippet(s)`);
