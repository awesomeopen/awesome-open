// Stage 5: record the catalog values the video shows, as published at the time of
// the run. Run it on the shoot date; the overlay and QC read only this file.
//   node scripts/facts.mjs <video> [--catalog <url or file>]
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { logStage, readJson, sha256, videoDir } from './lib.mjs';

const SITE = 'https://awesomeopen.github.io/awesome-open/';
const [id, flag, source = SITE + 'catalog.json'] = process.argv.slice(2);
if (flag && flag !== '--catalog') throw new Error('Unknown option ' + flag);
const dir = videoDir(id);
const beats = readJson(join(dir, '02-beats.json'));

const raw = existsSync(source) ? readFileSync(source) : Buffer.from(await (await fetch(source)).arrayBuffer());
const catalog = JSON.parse(raw.toString('utf8'));

// Labels follow the WebMCPlet list document (scripts/build_webmcplet_list.py).
const FIELDS = {
  github_stars: { label: 'GitHub stars', read: p => p.github?.stars ?? null, observed: p => p.github?.last_success_at },
  license: { label: 'Detected license', read: p => p.github?.license ?? null, observed: p => p.github?.last_success_at },
  pushed_at: { label: 'Last push', read: p => p.github?.pushed_at?.slice(0, 10) ?? null, observed: p => p.github?.last_success_at },
  run_modes: { label: 'Run mode', read: p => (p.deployment?.run_modes || []).map(m => m.value).join(', ') || null, observed: p => p.deployment?.checked_at }
};

const wanted = beats.overlays.filter(o => o.type === 'valueCheck');
const projects = {};
for (const overlay of wanted) {
  for (const name of overlay.projects) {
    const project = catalog.projects.find(p => p.name === name);
    if (!project) throw new Error(`${name} is not in the catalog`);
    projects[name] = projects[name] || { id: project.id, url: project.url, fields: {} };
    for (const field of overlay.fields) {
      const spec = FIELDS[field];
      if (!spec) throw new Error(`Unknown field ${field}; known: ${Object.keys(FIELDS).join(', ')}`);
      // null stays null and renders as Unknown.
      projects[name].fields[field] = { label: spec.label, value: spec.read(project), source: 'catalog', observed: spec.observed(project) || null };
    }
  }
}

const facts = {
  catalog: { source, fetched_at: new Date().toISOString(), sha256: sha256(raw), metrics_as_of: catalog.metrics_as_of, source_sha: catalog.source_sha },
  projects
};
writeFileSync(join(dir, '05-facts.json'), JSON.stringify(facts, null, 2) + '\n');
logStage(dir, 'facts', { catalog: facts.catalog.sha256 });
console.log(`05-facts.json: ${Object.keys(projects).length} projects from catalog ${facts.catalog.sha256.slice(0, 12)}`);
