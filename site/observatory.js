/* Catalog Observatory: local snapshot only. No requests or chart dependencies.
   Server-rendered markup in build_observatory.py and these renderers must match. */
(function (root, factory) {
  'use strict';
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root && root.document) {
    if (root.document.readyState === 'loading') {
      root.document.addEventListener('DOMContentLoaded', function () { api.init(root.document, root); });
    } else api.init(root.document, root);
  }
}(typeof window !== 'undefined' ? window : null, function () {
  'use strict';

  var DAY = 86400000;
  var RECENCY_BOUNDS = [30, 90, 365, 730];
  var RECENCY_LABELS = ['0–30 days', '31–90 days', '91–365 days', '366–730 days', 'Over 730 days', 'Unknown'];
  var AGE_BOUNDS = [365, 1826, 3653];
  var AGE_LABELS = ['0–365 days', '366–1,826 days', '1,827–3,653 days', 'Over 3,653 days', 'Unknown'];
  var CSV_COLUMNS = ['id', 'name', 'url', 'description', 'categories', 'github', 'stars', 'license', 'created_at', 'pushed_at', 'release_at', 'release_status', 'release_checked_at', 'metrics_as_of', 'source_sha', 'metrics_status', 'metrics_last_success_at', 'metrics_attempt_at', 'metrics_attempt_status', 'metrics_attempt_http_status', 'metrics_attempt_reason'];

  function knownLicense(project) {
    return typeof project.license === 'string' && project.license.trim() !== '';
  }

  function knownStars(project) {
    return typeof project.stars === 'number' && Number.isFinite(project.stars) && project.stars >= 0;
  }

  function compareText(a, b) {
    return a < b ? -1 : a > b ? 1 : 0;
  }

  function normalizeFilters(input, categories) {
    input = input || {};
    var category = String(input.category || 'all');
    var valid = (categories || []).some(function (item) { return item.id === category; });
    return {
      category: valid ? category : 'all',
      license: input.license === 'known' || input.license === 'unknown' ? input.license : 'all'
    };
  }

  function readFilters(search, categories) {
    var params = new URLSearchParams(search || '');
    return normalizeFilters({ category: params.get('category'), license: params.get('license') }, categories);
  }

  function filterSearch(filters) {
    var params = new URLSearchParams();
    if (filters.category !== 'all') params.set('category', filters.category);
    if (filters.license !== 'all') params.set('license', filters.license);
    var value = params.toString();
    return value ? '?' + value : '';
  }

  function filterProjects(projects, filters) {
    return projects.filter(function (project) {
      var categories = Array.isArray(project.categories) ? project.categories : [];
      return (filters.category === 'all' || categories.indexOf(filters.category) !== -1) &&
        (filters.license === 'all' || knownLicense(project) === (filters.license === 'known'));
    });
  }

  /* Parse UTC calendar days, rejecting impossible source dates and times before
     converting timestamp offsets to UTC. Date-only values are already UTC days. */
  function isoDay(value) {
    if (typeof value !== 'string') return null;
    var match = /^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|([+-])(\d{2}):(\d{2})))?$/.exec(value);
    if (!match) return null;
    var year = Number(match[1]);
    var month = Number(match[2]);
    var day = Number(match[3]);
    if (year < 1 || month < 1 || month > 12 || day < 1 || day > 31) return null;
    if (match[4] !== undefined && (Number(match[4]) > 23 || Number(match[5]) > 59 || Number(match[6]) > 59 || Number(match[8] || 0) > 23 || Number(match[9] || 0) > 59)) return null;
    var date = new Date(0);
    date.setUTCFullYear(year, month - 1, day);
    date.setUTCHours(0, 0, 0, 0);
    if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return null;
    if (match[4] !== undefined) {
      var timestamp = Date.parse(value);
      var utcYear = new Date(timestamp).getUTCFullYear();
      return Number.isFinite(timestamp) && utcYear >= 1 && utcYear <= 9999 ? Math.floor(timestamp / DAY) : null;
    }
    return Math.floor(date.getTime() / DAY);
  }

  function dateHistogram(projects, field, asOf, bounds, labels) {
    var snapshotDay = isoDay(asOf);
    var rows = labels.map(function (label) { return { label: label, count: 0 }; });
    projects.forEach(function (project) {
      var projectDay = isoDay(project[field]);
      var elapsed = snapshotDay === null || projectDay === null ? null : snapshotDay - projectDay;
      var index = rows.length - 1;
      if (elapsed !== null && elapsed >= 0) {
        index = bounds.findIndex(function (bound) { return elapsed <= bound; });
        if (index === -1) index = bounds.length;
      }
      rows[index].count += 1;
    });
    return rows;
  }

  function categoryCounts(projects, categories) {
    var counts = new Map(categories.map(function (category) { return [category.id, 0]; }));
    var unknown = 0;
    projects.forEach(function (project) {
      var matched = new Set();
      (Array.isArray(project.categories) ? project.categories : []).forEach(function (id) {
        if (counts.has(id)) matched.add(id);
      });
      if (!matched.size) unknown += 1;
      matched.forEach(function (id) { counts.set(id, counts.get(id) + 1); });
    });
    // Sorted by count; ties keep catalog order (Array#sort is stable). Unknown stays last.
    var rows = categories.map(function (category) { return { id: category.id, label: category.name, count: counts.get(category.id) }; })
      .sort(function (a, b) { return b.count - a.count; });
    if (unknown) rows.push({ id: 'unknown', label: 'Unknown', count: unknown });
    return rows;
  }

  function licenseCounts(projects) {
    var counts = new Map();
    var unknown = 0;
    projects.forEach(function (project) {
      if (!knownLicense(project)) { unknown += 1; return; }
      var license = project.license.trim();
      counts.set(license, (counts.get(license) || 0) + 1);
    });
    var rows = Array.from(counts, function (entry) { return { label: entry[0], count: entry[1] }; });
    rows.sort(function (a, b) { return b.count - a.count || compareText(a.label, b.label); });
    rows.push({ label: 'Unknown', count: unknown });
    return rows;
  }

  function starConcentration(projects) {
    var mapped = projects.filter(function (project) { return project.github === true && knownStars(project); });
    mapped.sort(function (a, b) { return b.stars - a.stars || compareText(a.name, b.name) || compareText(a.id, b.id); });
    var top = mapped.slice(0, 10);
    var rest = mapped.slice(10);
    var total = mapped.reduce(function (sum, project) { return sum + project.stars; }, 0);
    var topTotal = top.reduce(function (sum, project) { return sum + project.stars; }, 0);
    var rows = top.map(function (project) { return { id: project.id, label: project.name, count: project.stars }; });
    if (rest.length) rows.push({ label: 'Other mapped projects', count: rest.reduce(function (sum, project) { return sum + project.stars; }, 0) });
    return { rows: rows, total: mapped.length || !projects.length ? total : null, topTotal: topTotal, topCount: top.length, share: total ? topTotal / total : null };
  }

  // Match Python's Unicode code-point ordering, including supplementary letters.
  function compareName(a, b) {
    var left = Array.from(a), right = Array.from(b);
    for (var i = 0; i < Math.min(left.length, right.length); i += 1) {
      var difference = left[i].codePointAt(0) - right[i].codePointAt(0);
      if (difference) return difference;
    }
    return left.length - right.length;
  }

  // Unicode White_Space (shared with build_observatory.py) plus hyphen and underscore.
  var NAME_SEPARATORS = /[\u0009-\u000d\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000_-]/g;
  var NAME_TAGS = ['Case', 'Spacing', 'Plural', 'Spelling', 'Exact duplicates'];
  // [result key, band label, legend label, ID prefix]
  var NAME_KINDS = [['identical', 'Identical names', 'Identical name', 'identical'], ['variants', 'Spelling variants', 'Spelling variants', 'variant']];

  function isSeparator(char) { NAME_SEPARATORS.lastIndex = 0; return NAME_SEPARATORS.test(char); }
  function nameKey(name) { return name.toLowerCase().replace(NAME_SEPARATORS, ''); }
  // The validated snapshot supplies reviewed equivalences; rhyme keys stay separate.
  function sharedNameKey(project) { return (project.name_match || {}).key || nameKey(project.name); }
  function nameAnatomy(name) {
    var chars = [], gaps = [''];
    Array.from(name).forEach(function (char) {
      if (isSeparator(char)) gaps[gaps.length - 1] += char;
      else { chars.push(char); gaps.push(''); }
    });
    return { chars: chars, gaps: gaps };
  }
  function nameDifferences(names) {
    var parts = names.map(nameAnatomy);
    return {
      chars: Array.from({ length: Math.max.apply(null, parts.map(function (p) { return p.chars.length; })) }, function (_, i) { return new Set(parts.map(function (p) { return p.chars[i]; })).size > 1; }),
      gaps: Array.from({ length: Math.max.apply(null, parts.map(function (p) { return p.gaps.length; })) }, function (_, i) { return new Set(parts.map(function (p) { return p.gaps[i] || ''; })).size > 1; })
    };
  }
  function hasCaseDifference(names) {
    var parts = names.map(function (name) { return nameAnatomy(name).chars; });
    return parts.some(function (left) { return parts.some(function (right) {
      return left.some(function (a, i) { var b = right[i]; return b !== undefined && a !== b && a.toLowerCase() === b.toLowerCase(); });
    }); });
  }
  function distinctNames(rows) { return Array.from(new Set(rows.map(function (project) { return project.name; }))).sort(compareName); }

  /* One matching key per displayed name, after canonical-ID deduplication. Equal
     keys form one group, so a project belongs to at most one group. */
  function sharedNames(projects) {
    var unique = new Map(projects.map(function (project) { return [project.id, project]; }));
    var ordered = Array.from(unique.values()).sort(function (a, b) { return compareName(a.name, b.name) || compareName(a.id, b.id); });
    var buckets = new Map();
    ordered.forEach(function (project) {
      var key = sharedNameKey(project);
      if (!key) return;
      if (!buckets.has(key)) buckets.set(key, []);
      buckets.get(key).push(project);
    });
    var result = { identical: [], variants: [], tags: {}, tool_count: 0, identical_tool_count: 0, variant_tool_count: 0 };
    NAME_TAGS.forEach(function (tag) { result.tags[tag] = 0; });
    buckets.forEach(function (rows) {
      if (rows.length < 2) return;
      var names = distinctNames(rows);
      var group = { name: names.join(' / '), names: names, projects: rows, tags: [] };
      if (names.length === 1) { result.identical.push(group); result.identical_tool_count += rows.length; return; }
      var differences = nameDifferences(names);
      var differentKeys = new Set(names.map(nameKey)).size > 1;
      var reasons = new Set(rows.map(function (project) { return (project.name_match || {}).reason; }));
      var present = [differentKeys ? hasCaseDifference(names) : differences.chars.some(Boolean), differences.gaps.some(Boolean),
        differentKeys && reasons.has('plural'), differentKeys && reasons.has('spelling'),
        names.some(function (name) { return rows.filter(function (project) { return project.name === name; }).length > 1; })];
      group.tags = NAME_TAGS.filter(function (_, i) { return present[i]; });
      group.tags.forEach(function (tag) { result.tags[tag] += 1; });
      result.variants.push(group);
      result.variant_tool_count += rows.length;
    });
    var byName = function (a, b) { return compareName(a.name, b.name); };
    result.identical.sort(byName);
    result.variants.sort(byName);
    result.tool_count = result.identical_tool_count + result.variant_tool_count;
    return result;
  }

  /* Reviewed pronunciations only: one non-chaining rhyme key per canonical ID.
     Distinct names and onsets exclude duplicate-only and homophone-only groups. */
  function rhymingNames(projects) {
    var unique = new Map(projects.map(function (project) { return [project.id, project]; }));
    var buckets = new Map(), result = { groups: [], tool_count: 0, reviewed_count: 0 };
    Array.from(unique.values()).sort(function (a, b) { return compareName(a.name, b.name) || compareName(a.id, b.id); }).forEach(function (project) {
      var rhyme = project.rhyme;
      if (!rhyme || rhyme.language !== 'en-US' || typeof rhyme.key !== 'string' || !rhyme.key ||
          typeof rhyme.onset !== 'string' || typeof rhyme.pronunciation !== 'string' || !rhyme.pronunciation) return;
      result.reviewed_count += 1;
      if (!buckets.has(rhyme.key)) buckets.set(rhyme.key, []);
      buckets.get(rhyme.key).push(project);
    });
    Array.from(buckets.keys()).sort(compareText).forEach(function (key) {
      var rows = buckets.get(key);
      if (rows.length < 2 || new Set(rows.map(function (project) { return nameKey(project.name); })).size < 2 ||
          new Set(rows.map(function (project) { return project.rhyme.onset; })).size < 2) return;
      result.groups.push({ key: key, language: 'en-US', projects: rows });
      result.tool_count += rows.length;
    });
    return result;
  }

  function renderRhymingNames(doc, result) {
    var list = doc.getElementById('rhyme-group-list');
    if (!list) return;
    var fragment = doc.createDocumentFragment();
    var ledgerBase = list.dataset.ledgerBase || '../';
    result.groups.forEach(function (group) {
      var section = element(doc, 'section', 'obs-rhyme-group');
      section.dataset.rhymeKey = group.key;
      section.appendChild(element(doc, 'h3', 'obs-label', group.key + ' · ' + group.projects.length + ' tools'));
      var links = element(doc, 'ul', 'obs-rhyme-projects');
      group.projects.forEach(function (project) {
        var item = element(doc, 'li'), link = element(doc, 'a', null, project.name);
        link.href = ledgerBase + '#project-' + project.id;
        item.append(link, element(doc, 'span', 'obs-muted', '(' + project.url.replace(/^https?:\/\/(github\.com\/)?/, '') + ') · ' + project.rhyme.pronunciation));
        links.appendChild(item);
      });
      section.appendChild(links);
      fragment.appendChild(section);
    });
    if (!result.groups.length) fragment.appendChild(element(doc, 'p', 'obs-muted', 'No reviewed rhyming names in this selection.'));
    list.replaceChildren(fragment);
    var total = doc.getElementById('rhyme-count');
    if (total) total.textContent = formatNumber(result.tool_count);
    var summary = doc.getElementById('rhyme-group-summary');
    if (summary) summary.textContent = result.groups.length + ' groups · ' + result.reviewed_count + ' reviewed readings';
  }

  function element(doc, tag, className, text) {
    var node = doc.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function appendMarkedName(doc, parent, name, names) {
    if (names.length < 2) { parent.appendChild(doc.createTextNode(name)); return; }
    var differences = nameDifferences(names), anatomy = nameAnatomy(name);
    anatomy.gaps.forEach(function (gap, i) {
      if (gap) parent.appendChild(differences.gaps[i] ? element(doc, 'span', 'name-diff name-gap', gap) : doc.createTextNode(gap));
      else if (differences.gaps[i]) { var bar = element(doc, 'span', 'name-diff name-nogap'); bar.setAttribute('aria-hidden', 'true'); parent.appendChild(bar); }
      if (i < anatomy.chars.length) parent.appendChild(differences.chars[i] ? element(doc, 'span', 'name-diff', anatomy.chars[i]) : doc.createTextNode(anatomy.chars[i]));
    });
  }
  function categoryNames(project, categories) {
    return (project.categories || []).map(function (id) { return categories.get(id) || 'Unknown'; }).join(', ') || 'Unknown';
  }
  function repositoryLink(doc, url) {
    var link = element(doc, 'a', 'obs-repo');
    link.href = url;
    var github = 'https://github.com/';
    if (url.indexOf(github) === 0) {
      var rest = url.slice(github.length), slash = rest.indexOf('/');
      var owner = slash === -1 ? rest : rest.slice(0, slash);
      link.append(element(doc, 'span', 'obs-repo-path', 'github.com/'), element(doc, 'span', 'obs-repo-owner', owner),
        element(doc, 'span', 'obs-repo-path', '/' + (slash === -1 ? '' : rest.slice(slash + 1))));
    } else link.append(element(doc, 'span', 'obs-repo-path', url.replace(/^https?:\/\//, '')));
    return link;
  }
  function namePlate(doc, group, number, categories) {
    var id = 'name-group-' + number, rows = group.projects;
    var plate = element(doc, 'article', 'shared-name-group');
    plate.id = id;
    plate.dataset.name = group.name;
    plate.setAttribute('aria-labelledby', id + '-heading');
    var head = element(doc, 'header', 'obs-plate-head');
    var heading = element(doc, 'h4');
    heading.id = id + '-heading';
    group.names.forEach(function (name, i) {
      if (i) heading.appendChild(element(doc, 'span', 'obs-name-sep', '/'));
      appendMarkedName(doc, heading, name, group.names);
    });
    var meta = element(doc, 'p', 'obs-plate-meta');
    meta.appendChild(element(doc, 'strong', null, rows.length + ' tools'));
    group.tags.forEach(function (tag) { meta.append(doc.createTextNode(' '), element(doc, 'span', 'obs-tag', tag)); });
    var common = [];
    var category = categoryNames(rows[0], categories);
    if (rows.every(function (project) { return categoryNames(project, categories) === category; })) common.push(category);
    var license = rows[0].license || 'Unknown';
    if (rows.every(function (project) { return (project.license || 'Unknown') === license; })) common.push(license);
    if (common.length) meta.appendChild(doc.createTextNode(' · In common: ' + common.join(' · ')));
    head.append(heading, meta);
    var grid = element(doc, 'div', 'obs-plate-projects');
    grid.style.setProperty('--n', String(rows.length));
    rows.forEach(function (project) {
      var column = element(doc, 'div', 'obs-plate-project');
      column.dataset.projectId = project.id;
      var name = element(doc, 'p', 'obs-plate-name');
      appendMarkedName(doc, name, project.name, group.names);
      var facts = element(doc, 'dl', 'obs-plate-facts');
      [['Category', categoryNames(project, categories)], ['License', project.license || null],
        ['GitHub stars', knownStars(project) ? formatNumber(project.stars) : null],
        ['Created', project.created_at ? project.created_at.slice(0, 10) : null],
        ['Last push', project.pushed_at ? project.pushed_at.slice(0, 10) : null],
        ['Metrics cache', metricsCacheLabel(project)]].forEach(function (fact) {
        facts.append(element(doc, 'dt', null, fact[0]), element(doc, 'dd', fact[1] === null ? 'obs-unknown' : null, fact[1] === null ? 'Unknown' : fact[1]));
      });
      var record = element(doc, 'a', 'obs-record', 'OP-' + project.id.slice(0, 8).toUpperCase());
      record.href = (doc.querySelector('[data-ledger-base]')?.dataset.ledgerBase || '../') + '#project-' + project.id;
      record.setAttribute('aria-label', 'Catalog record for ' + project.name + ' (' + project.url.replace(/^https?:\/\/(github\.com\/)?/, '') + ')');
      var value = element(doc, 'dd');
      value.appendChild(record);
      facts.append(element(doc, 'dt', null, 'Catalog'), value);
      var intro = element(doc, 'div', 'obs-plate-intro');
      if (project.specimen) {
        var art = project.specimen, image = element(doc, 'img', 'obs-pair-art');
        image.src = art.path;
        image.alt = art.alt;
        image.width = art.width;
        image.height = art.height;
        image.loading = 'lazy';
        image.decoding = 'async';
        intro.appendChild(image);
      }
      var copy = element(doc, 'div', 'obs-plate-copy');
      copy.append(name, repositoryLink(doc, project.url), element(doc, 'p', 'obs-plate-desc', project.description || 'No short description in the catalog.'));
      intro.appendChild(copy);
      column.append(intro, facts);
      grid.appendChild(column);
    });
    plate.append(head, grid);
    return plate;
  }

  function renderSharedNames(doc, result, categories) {
    var tally = doc.getElementById('name-tally'), bands = doc.getElementById('name-group-bands');
    if (!tally || !bands) return;
    var clusters = doc.createDocumentFragment(), bandFragment = doc.createDocumentFragment(), number = 0, marks = 0;
    NAME_KINDS.forEach(function (kind) {
      var groups = result[kind[0]];
      if (groups.length && marks) clusters.appendChild(element(doc, 'span', 'obs-tally-break'));
      var band = element(doc, 'section', 'obs-name-band');
      band.setAttribute('aria-labelledby', kind[3] + '-names-heading');
      var count = result[kind[0] === 'identical' ? 'identical_tool_count' : 'variant_tool_count'];
      var heading = element(doc, 'h3', 'obs-label', kind[1] + ' · ' + count + ' tools');
      heading.id = kind[3] + '-names-heading';
      var container = element(doc, 'div');
      container.id = kind[3] + '-name-groups';
      groups.forEach(function (group) {
        number += 1;
        var cluster = element(doc, 'a', 'obs-cluster');
        cluster.href = '#name-group-' + number;
        var projectLabels = group.projects.map(function (project) {
          return project.name + ' (' + project.url.replace(/^https?:\/\/(github\.com\/)?/, '') + ')';
        });
        cluster.title = projectLabels.join('; ');
        cluster.setAttribute('aria-label', group.name + ', ' + group.projects.length + ' tools, ' + kind[2].toLowerCase() + ': ' + cluster.title);
        projectLabels.forEach(function (label) {
          var mark = element(doc, 'span', 'obs-mark obs-mark-' + kind[0]);
          mark.title = label;
          cluster.appendChild(mark);
          marks += 1;
        });
        clusters.appendChild(cluster);
        container.appendChild(namePlate(doc, group, number, categories));
      });
      if (!groups.length) container.appendChild(element(doc, 'p', 'obs-empty', 'No ' + kind[2].toLowerCase() + ' in this selection.'));
      band.append(heading, container);
      bandFragment.appendChild(band);
      var legendCount = doc.getElementById(kind[3] + '-name-count');
      if (legendCount) {
        legendCount.textContent = String(count);
        legendCount.parentElement.classList.toggle('obs-zero', !count);
      }
    });
    if (!marks) clusters.appendChild(element(doc, 'p', 'obs-muted', 'No shared names in this selection.'));
    tally.replaceChildren(clusters);
    bands.replaceChildren(bandFragment);
    var groupCount = result.identical.length + result.variants.length;
    var summary = doc.getElementById('name-group-summary');
    if (summary) summary.textContent = groupCount + (groupCount === 1 ? ' group · ' : ' groups · ') + result.tool_count + ' tools';
    var total = doc.getElementById('shared-name-count');
    if (total) total.textContent = formatNumber(result.tool_count);
  }

  function aggregate(data, filters) {
    filters = normalizeFilters(filters, data.categories);
    var projects = filterProjects(data.projects, filters);
    var stars = starConcentration(projects);
    var push = dateHistogram(projects, 'pushed_at', data.metrics_as_of, RECENCY_BOUNDS, RECENCY_LABELS);
    var release = dateHistogram(projects, 'release_at', data.metrics_as_of, RECENCY_BOUNDS, RECENCY_LABELS);
    return {
      sharedNames: sharedNames(projects),
      rhymingNames: rhymingNames(projects),
      filters: filters,
      projects: projects,
      metrics: {
        total: projects.length,
        mapped: projects.filter(function (project) { return project.github === true; }).length,
        stars: stars.total,
        'known-license': projects.filter(knownLicense).length
      },
      categories: categoryCounts(projects, data.categories),
      licenses: licenseCounts(projects),
      age: dateHistogram(projects, 'created_at', data.metrics_as_of, AGE_BOUNDS, AGE_LABELS),
      push: push,
      release: release,
      concentration: stars,
      // Push and release share one maximum so their bars compare directly.
      recencyMaximum: push.concat(release).reduce(function (value, row) { return Math.max(value, row.count); }, 0)
    };
  }

  function csvCell(value) {
    var text = value === null || value === undefined ? '' : String(value);
    // Quote CSV syntax and neutralize spreadsheet expressions, including those
    // preceded by whitespace/control characters. Unknown fields remain empty.
    if (/^[\u0000-\u0020]*[=+\-@]/.test(text) || /^[\t\r\n]/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  }

  function exportCSV(data, projects) {
    var lines = [CSV_COLUMNS.map(csvCell).join(',')];
    (projects || data.projects).forEach(function (project) {
      var values = CSV_COLUMNS.map(function (key) {
        if (key === 'metrics_as_of' || key === 'source_sha') return data[key];
        if (key === 'categories') return (project.categories || []).join('; ');
        if (key === 'github') return project.github === true ? 'true' : 'false';
        return project[key];
      });
      lines.push(values.map(csvCell).join(','));
    });
    return lines.join('\r\n') + '\r\n';
  }

  function metricsCacheLabel(project) {
    return (project.metrics_status || 'unknown') + (project.metrics_last_success_at
      ? ' · observed ' + project.metrics_last_success_at + ' UTC' : ' · no successful observation');
  }

  function formatNumber(value) {
    return value === null ? 'Unknown' : new Intl.NumberFormat('en-US').format(value);
  }

  function barWidth(value, maximum) { return (maximum ? 100 * value / maximum : 0).toFixed(4) + '%'; }

  // Zero-based linear bars; the folded table is the accessible equivalent.
  function renderChart(doc, container, rows, valueLabel, sharedMaximum) {
    if (!container) return;
    var max = typeof sharedMaximum === 'number' ? sharedMaximum : rows.reduce(function (value, row) { return Math.max(value, row.count); }, 0);
    var tbody = container.querySelector('tbody');
    if (tbody) {
      var fragment = doc.createDocumentFragment();
      rows.forEach(function (row) {
        var tr = doc.createElement('tr');
        tr.setAttribute('data-key', row.label);
        tr.setAttribute('data-count', row.count);
        var label = element(doc, 'th', null, row.label);
        label.setAttribute('scope', 'row');
        tr.append(label, element(doc, 'td', null, formatNumber(row.count)));
        fragment.appendChild(tr);
      });
      if (!rows.length) {
        var empty = doc.createElement('tr');
        var cell = element(doc, 'td', null, 'No observed values in this selection.');
        cell.colSpan = 2;
        empty.appendChild(cell);
        fragment.appendChild(empty);
      }
      tbody.replaceChildren(fragment);
    }
    var list = container.querySelector('.obs-bar-list');
    if (!list) return;
    var scale = container.querySelector('.obs-scale-max');
    if (scale) scale.textContent = formatNumber(max) + ' ' + (valueLabel || 'projects') + (typeof sharedMaximum === 'number' ? ' · shared scale' : '');
    var bars = doc.createDocumentFragment();
    rows.forEach(function (row) {
      var item = element(doc, 'li', row.label === 'Unknown' ? 'obs-bar obs-bar-unknown' : 'obs-bar');
      item.setAttribute('data-key', row.label);
      item.setAttribute('data-count', row.count);
      var track = element(doc, 'span', 'obs-track'), fill = element(doc, 'span', 'obs-fill');
      fill.style.width = barWidth(row.count, max);
      track.appendChild(fill);
      item.append(element(doc, 'span', 'obs-bar-label', row.label), track, element(doc, 'span', 'obs-bar-count', formatNumber(row.count)));
      bars.appendChild(item);
    });
    list.replaceChildren(bars);
    var emptyNote = container.querySelector('.obs-bars > .obs-empty');
    if (!rows.length && !emptyNote) list.after(element(doc, 'p', 'obs-empty', 'No observed values in this selection.'));
    if (rows.length && emptyNote) emptyNote.remove();
  }

  function init(doc, win) {
    var source = doc.getElementById('observatory-data');
    var form = doc.getElementById('observatory-filters');
    if (!source || !form || form.dataset.enhanced === 'true') return null;
    var data;
    try { data = JSON.parse(source.textContent); } catch (_) { return null; }
    if (!data || data.schema_version !== 1 || !Array.isArray(data.projects) || !Array.isArray(data.categories)) return null;
    var category = doc.getElementById('category-filter');
    var license = doc.getElementById('license-filter');
    if (!category || !license) return null;
    var reset = doc.getElementById('reset-filters');
    var categoryMap = new Map(data.categories.map(function (item) { return [item.id, item.name]; }));
    var groupsDisclosure = doc.getElementById('name-groups');
    var tallyNode = doc.getElementById('name-tally');
    // A tally cluster opens the folded name groups before the browser follows its link.
    if (tallyNode && groupsDisclosure) tallyNode.addEventListener('click', function (event) {
      if (event.target.closest && event.target.closest('.obs-cluster')) groupsDisclosure.open = true;
    });
    var summary = doc.getElementById('selection-summary');
    var download = doc.getElementById('export-csv');
    var objectURL = null;

    function setLocation(filters, replace) {
      var target = win.location.pathname + filterSearch(filters) + win.location.hash;
      if (target === win.location.pathname + win.location.search + win.location.hash) return;
      // A sandboxed/offline document may prohibit history updates; its local
      // filtering and export remain usable in that case.
      try { win.history[replace ? 'replaceState' : 'pushState'](null, '', target); } catch (_) { /* native fallback */ }
    }

    function apply(filters, updateLocation, replace) {
      var result = aggregate(data, filters);
      category.value = result.filters.category === 'all' && Array.from(category.options).some(function (option) { return option.value === ''; }) ? '' : result.filters.category;
      license.value = result.filters.license;
      var selectedOption = category.options[category.selectedIndex];
      var metricArt = selectedOption && selectedOption.getAttribute('data-metric-art');
      doc.querySelectorAll('.obs-metric').forEach(function (node, index) {
        node.style.backgroundImage = index === 0 && metricArt ? 'url("' + metricArt + '")' : '';
      });
      if (updateLocation) setLocation(result.filters, replace);
      doc.querySelectorAll('[data-metric]').forEach(function (node) {
        var key = node.getAttribute('data-metric');
        if (Object.prototype.hasOwnProperty.call(result.metrics, key)) node.textContent = formatNumber(result.metrics[key]);
      });
      doc.querySelectorAll('[data-metric-of]').forEach(function (node) { node.textContent = formatNumber(result.metrics.total); });
      doc.querySelectorAll('[data-ratio]').forEach(function (node) {
        node.style.width = barWidth(result.metrics[node.getAttribute('data-ratio')], result.metrics.total);
      });
      if (summary) summary.textContent = formatNumber(result.metrics.total) + '/' + formatNumber(data.projects.length) + ' selected.';
      if (reset) reset.disabled = result.filters.category === 'all' && result.filters.license === 'all';
      renderSharedNames(doc, result.sharedNames, categoryMap);
      renderRhymingNames(doc, result.rhymingNames);
      renderChart(doc, doc.getElementById('category-chart'), result.categories);
      renderChart(doc, doc.getElementById('license-chart'), result.licenses);
      renderChart(doc, doc.getElementById('star-chart'), result.concentration.rows, 'stars');
      renderChart(doc, doc.getElementById('age-chart'), result.age);
      renderChart(doc, doc.getElementById('push-chart'), result.push, 'projects', result.recencyMaximum);
      renderChart(doc, doc.getElementById('release-chart'), result.release, 'projects', result.recencyMaximum);
      if (download) {
        var csv = exportCSV(data, result.projects);
        if (win.Blob && win.URL && win.URL.createObjectURL) {
          var nextURL = win.URL.createObjectURL(new win.Blob([csv], { type: 'text/csv;charset=utf-8' }));
          download.href = nextURL;
          if (objectURL) win.URL.revokeObjectURL(objectURL);
          objectURL = nextURL;
        } else download.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv);
        download.download = 'awesome-open-observatory-' + String(data.metrics_as_of).slice(0, 10) + '.csv';
        download.setAttribute('aria-label', 'Download CSV for ' + result.projects.length + ' selected projects');
      }
      return result;
    }

    function onChange() { apply({ category: category.value, license: license.value }, true, false); }
    category.addEventListener('change', onChange);
    license.addEventListener('change', onChange);
    form.addEventListener('submit', function (event) { event.preventDefault(); onChange(); });
    if (reset) reset.addEventListener('click', function (event) { event.preventDefault(); apply({ category: 'all', license: 'all' }, true, false); });
    win.addEventListener('popstate', function () { apply(readFilters(win.location.search, data.categories), true, true); });
    apply(readFilters(win.location.search, data.categories), true, true);
    form.dataset.enhanced = 'true';
    form.hidden = false;
    return { apply: apply, data: data };
  }

  return {
    AGE_BOUNDS: AGE_BOUNDS, AGE_LABELS: AGE_LABELS,
    RECENCY_BOUNDS: RECENCY_BOUNDS, RECENCY_LABELS: RECENCY_LABELS,
    CSV_COLUMNS: CSV_COLUMNS, metricsCacheLabel: metricsCacheLabel, knownLicense: knownLicense, knownStars: knownStars,
    normalizeFilters: normalizeFilters, readFilters: readFilters, filterSearch: filterSearch,
    filterProjects: filterProjects, isoDay: isoDay, dateHistogram: dateHistogram,
    categoryCounts: categoryCounts, licenseCounts: licenseCounts, starConcentration: starConcentration,
    nameKey: nameKey, sharedNames: sharedNames, rhymingNames: rhymingNames, aggregate: aggregate, csvCell: csvCell, exportCSV: exportCSV,
    renderChart: renderChart, renderSharedNames: renderSharedNames, renderRhymingNames: renderRhymingNames, init: init
  };
}));

