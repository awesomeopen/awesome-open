// V2 draw. The seed is SHA-256 of the screening file and the shoot date, so the
// draw is fixed once screening is committed and anyone can repeat it.
//   node scripts/draw.mjs v2 2026-11-17
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { logStage, readJson, sha256, sha256File, videoDir } from './lib.mjs';

const [id, date] = process.argv.slice(2);
if (!/^\d{4}-\d{2}-\d{2}$/.test(date || '')) throw new Error('Usage: node scripts/draw.mjs v2 YYYY-MM-DD (the shoot date)');
const dir = videoDir(id);
const screening = sha256File(join(dir, '00-screening.json'));
const passing = readJson(join(dir, '00-screening.json')).results.filter(r => r.passes);
const seed = sha256(screening + ' ' + date);
const index = Number(BigInt('0x' + seed) % BigInt(passing.length));
const draw = { date, screening_sha256: screening, seed, pool: passing.map(r => r.repo), index, drawn: passing[index] };
writeFileSync(join(dir, '00-draw.json'), JSON.stringify(draw, null, 2) + '\n');
logStage(dir, 'draw', { screening });
console.log(`Seed ${seed.slice(0, 12)} → ${index} of ${passing.length}: ${draw.drawn.repo} ("${draw.drawn.ask}")`);
