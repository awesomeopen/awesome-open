// Stage 5: record the catalog values the video shows, as published at the time of
// the run. Run it on the shoot date; the overlay and QC read only this file.
//   node scripts/facts.mjs <video> [--catalog <url or file>]
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { logStage, readJson, sha256, sha256File, videoDir } from './lib.mjs';

const SITE = 'https://awesomeopen.github.io/awesome-open/';
const [id, flag, source = SITE + 'catalog.json'] = process.argv.slice(2);
if (flag && flag !== '--catalog') throw new Error('Unknown option ' + flag);
const dir = videoDir(id);
const beats = readJson(join(dir, '02-beats.json'));

const needsCatalog = beats.overlays.some(o => (o.type === 'valueCheck' && !o.list) || (o.type === 'claims' && o.items.some(i => i.source === 'catalog')));
const raw = !needsCatalog ? null : existsSync(source) ? readFileSync(source) : Buffer.from(await (await fetch(source)).arrayBuffer());
const catalog = raw ? JSON.parse(raw.toString('utf8')) : null;

// Labels follow the WebMCPlet list document (scripts/build_webmcplet_list.py).
const FIELDS = {
  github_stars: { label: 'GitHub stars', read: p => p.github?.stars ?? null, observed: p => p.github?.last_success_at },
  license: { label: 'Detected license', read: p => p.github?.license ?? null, observed: p => p.github?.last_success_at },
  pushed_at: { label: 'Last push', read: p => p.github?.pushed_at?.slice(0, 10) ?? null, observed: p => p.github?.last_success_at },
  run_modes: { label: 'Run mode', read: p => (p.deployment?.run_modes || []).map(m => m.value).join(', ') || null, observed: p => p.deployment?.checked_at }
};

const wanted = beats.overlays.filter(o => o.type === 'valueCheck');
const projects = {};
for (const overlay of wanted.filter(o => o.list)) {
  // Values from another list's document as served during the shoot (V2), with
  // that document's field labels and observation dates.
  const doc = readJson(join(dir, overlay.list));
  for (const name of overlay.projects) {
    const item = doc.items.find(i => i.name === name);
    if (!item) throw new Error(`${name} is not in ${overlay.list}`);
    projects[name] = { id: item.id, url: item.url, fields: {} };
    for (const field of overlay.fields) {
      const spec = doc.fields?.[field];
      if (!spec) throw new Error(`${overlay.list} declares no field ${field}`);
      projects[name].fields[field] = { label: spec.label, value: item.fields?.[field] ?? null, source: 'list', observed: spec.observed_at || null };
    }
  }
}
for (const overlay of wanted.filter(o => !o.list)) {
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

// Claims the client makes. A catalog claim must quote text found in the project's
// record, so the tag "Catalog" is checked; web and generated claims are transcribed
// from the capture with what the client cited.
const claims = [];
for (const overlay of beats.overlays.filter(o => o.type === 'claims')) {
  for (const item of overlay.items) {
    const entry = { ...item };
    if (item.source === 'catalog') {
      const project = catalog.projects.find(p => p.name === item.project);
      if (!project) throw new Error(`${item.project} is not in the catalog`);
      const text = JSON.stringify(project);
      if (!item.match || !text.includes(item.match)) throw new Error(`${item.project}: "${item.match}" is not in its catalog record`);
      entry.observed = project.function_summary?.checked_at || null;
      entry.verified = true;
    }
    claims.push(entry);
  }
}

const facts = {
  catalog: raw ? { source, fetched_at: new Date().toISOString(), sha256: sha256(raw), metrics_as_of: catalog.metrics_as_of, source_sha: catalog.source_sha } : null,
  lists: Object.fromEntries(wanted.filter(o => o.list).map(o => [o.list, sha256File(join(dir, o.list))])),
  projects,
  claims
};
writeFileSync(join(dir, '05-facts.json'), JSON.stringify(facts, null, 2) + '\n');
logStage(dir, 'facts', { ...(facts.catalog ? { catalog: facts.catalog.sha256 } : {}), ...facts.lists });
console.log(`05-facts.json: ${Object.keys(projects).length} projects, ${claims.length} claims`);
