// V2 screening: licence, import and query check for each candidate list, at its
// current revision. Writes 00-screening.json and .md beside 00-pool.json.
//   GITHUB_TOKEN=… node scripts/screen.mjs v2
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { REPO, logStage, readJson, sha256, sha256File, videoDir } from './lib.mjs';

const require = createRequire(import.meta.url);
const { importMarkdown } = require(join(REPO, 'webmcplet/markdown.js'));
const { create } = require(join(REPO, 'webmcplet/webmcplet.js'));
const id = process.argv[2];
const dir = videoDir(id);
const pool = readJson(join(dir, '00-pool.json'));
const headers = { 'user-agent': 'awesome-open launch-video screening', ...(process.env.GITHUB_TOKEN ? { authorization: 'Bearer ' + process.env.GITHUB_TOKEN } : {}) };
const api = async path => { const r = await fetch('https://api.github.com/' + path, { headers }); if (!r.ok) throw new Error(path + ' ' + r.status); return r.json(); };

const results = [];
for (const c of pool.candidates) {
  const meta = await api('repos/' + c.repo);
  const revision = (await api(`repos/${c.repo}/commits/${meta.default_branch}`)).sha;
  const markdown = await (await fetch(`https://raw.githubusercontent.com/${c.repo}/${revision}/README.md`)).text();
  const licence = c.licence_override?.spdx || meta.license?.spdx_id || null;
  const r = { repo: c.repo, revision, readme_sha256: sha256(markdown), licence, licence_evidence: c.licence_override?.evidence || 'GitHub license metadata', reasons: [] };
  if (!pool.licences_allowed.includes(licence)) r.reasons.push(`licence ${licence ?? 'none'} is not in the allowed list`);
  try {
    const { doc, counts } = importMarkdown(markdown, { title: c.repo, page_url: 'https://github.com/' + c.repo });
    Object.assign(r, { items: counts.items, entries: counts.entries, skipped: counts.skipped, sections: doc.sections.length });
    if (c.section && !doc.sections.some(s => s.title === c.section)) r.reasons.push(`no section "${c.section}"`);
    r.results = create(doc).find({ query: c.query }).total;
    if (r.results < pool.minimum_results) r.reasons.push(`"${c.query}" returns ${r.results}`);
  } catch (error) {
    r.reasons.push('import fails: ' + error.message.split('\n')[0]);
  }
  r.passes = r.reasons.length === 0;
  results.push({ ...c, ...r });
}

const screened = { screened_at: new Date().toISOString(), pool_sha256: sha256File(join(dir, '00-pool.json')), results };
writeFileSync(join(dir, '00-screening.json'), JSON.stringify(screened, null, 2) + '\n');
const md = ['# V2 screening', '', `Screened ${screened.screened_at}. ${results.filter(r => r.passes).length} of ${results.length} lists pass.`, '',
  '| List | Revision | Licence | Items | Query | Results | Passes |', '| --- | --- | --- | --- | --- | --- | --- |',
  ...results.map(r => `| ${r.repo} | \`${r.revision.slice(0, 7)}\` | ${r.licence ?? 'none'} | ${r.items ?? '–'} | "${r.query}" | ${r.results ?? '–'} | ${r.passes ? 'yes' : 'no: ' + r.reasons.join('; ')} |`), ''];
writeFileSync(join(dir, '00-screening.md'), md.join('\n'));
logStage(dir, 'screen', { pool: screened.pool_sha256 });
console.log(md.slice(2, 3).join(''));
