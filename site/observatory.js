/* Catalog Observatory: local snapshot only. No requests or chart dependencies. */
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
  var SVG_NS = 'http://www.w3.org/2000/svg';
  var RECENCY_BOUNDS = [30, 90, 365, 730];
  var RECENCY_LABELS = ['0–30 days', '31–90 days', '91–365 days', '366–730 days', 'Over 730 days', 'Unknown'];
  var AGE_BOUNDS = [365, 1826, 3653];
  var AGE_LABELS = ['0–365 days', '366–1,826 days', '1,827–3,653 days', 'Over 3,653 days', 'Unknown'];
  var CSV_COLUMNS = ['id', 'name', 'url', 'categories', 'github', 'stars', 'license', 'created_at', 'pushed_at', 'release_at', 'release_status', 'release_checked_at', 'metrics_as_of', 'source_sha'];

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
    var rows = categories.map(function (category) { return { id: category.id, label: category.name, count: counts.get(category.id) }; });
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
    return { rows: rows, total: total, topTotal: topTotal, topCount: top.length, share: total ? topTotal / total : null };
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

  function sharedNames(projects) {
    var unique = new Map(projects.map(function (project) { return [project.id, project]; }));
    var ordered = Array.from(unique.values()).sort(function (a, b) { return compareName(a.name, b.name) || compareName(a.id, b.id); });
    var exact = new Map();
    ordered.forEach(function (project) {
      if (!exact.has(project.name)) exact.set(project.name, []);
      exact.get(project.name).push(project);
    });
    var groups = Array.from(exact, function (entry) { return { name: entry[0], projects: entry[1] }; }).filter(function (group) { return group.projects.length > 1; });
    var exactIDs = new Set(groups.flatMap(function (group) { return group.projects.map(function (project) { return project.id; }); }));
    var folded = new Map();
    ordered.forEach(function (project) {
      if (exactIDs.has(project.id)) return;
      var key = project.name.toLowerCase();
      if (!folded.has(key)) folded.set(key, []);
      folded.get(key).push(project);
    });
    var capitalization = Array.from(folded.values()).filter(function (rows) { return rows.length > 1; }).map(function (rows) {
      return { name: Array.from(new Set(rows.map(function (project) { return project.name; }))).sort(compareName).join(' / '), projects: rows };
    }).sort(function (a, b) { return compareName(a.name, b.name); });
    var countedIDs = new Set([...exactIDs, ...capitalization.flatMap(function (group) { return group.projects.map(function (project) { return project.id; }); })]);
    var compacted = new Map();
    ordered.forEach(function (project) {
      if (countedIDs.has(project.id)) return;
      // Unicode White_Space, shared with build_observatory.py; preserve case.
      var key = project.name.replace(/[\u0009-\u000d\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]/g, '');
      if (!key) return;
      if (!compacted.has(key)) compacted.set(key, []);
      compacted.get(key).push(project);
    });
    var whitespace = Array.from(compacted.values()).filter(function (rows) {
      return new Set(rows.map(function (project) { return project.name; })).size > 1;
    }).map(function (rows) {
      return { name: Array.from(new Set(rows.map(function (project) { return project.name; }))).sort(compareName).join(' / '), projects: rows };
    }).sort(function (a, b) { return compareName(a.name, b.name); });
    whitespace.forEach(function (group) { group.projects.forEach(function (project) { countedIDs.add(project.id); }); });
    return { exact: groups, capitalization: capitalization, whitespace: whitespace, tool_count: countedIDs.size,
      exact_tool_count: exactIDs.size,
      capitalization_tool_count: capitalization.reduce(function (sum, group) { return sum + group.projects.length; }, 0),
      whitespace_tool_count: whitespace.reduce(function (sum, group) { return sum + group.projects.length; }, 0) };
  }

  function renderNameGroups(doc, container, groups) {
    if (!container) return;
    var openNames = new Set(Array.from(container.querySelectorAll('details[open]')).map(function (detail) { return detail.dataset.name; }));
    var fragment = doc.createDocumentFragment();
    groups.forEach(function (group) {
      var detail = doc.createElement('details');
      detail.className = 'shared-name-group';
      detail.dataset.name = group.name;
      detail.open = openNames.has(group.name);
      var summary = doc.createElement('summary');
      summary.textContent = group.name + ' · ' + group.projects.length + ' tools';
      detail.appendChild(summary);
      var list = doc.createElement('ul');
      group.projects.forEach(function (project) {
        var item = doc.createElement('li');
        item.dataset.projectId = project.id;
        var link = doc.createElement('a');
        link.href = project.url;
        link.textContent = project.name;
        var source = doc.createElement('span');
        source.className = 'shared-name-source';
        source.textContent = project.url;
        item.appendChild(link);
        item.appendChild(source);
        list.appendChild(item);
      });
      detail.appendChild(list);
      fragment.appendChild(detail);
    });
    if (!groups.length) {
      var empty = doc.createElement('p');
      empty.textContent = 'No shared names in this selection.';
      fragment.appendChild(empty);
    }
    container.replaceChildren(fragment);
  }

  function aggregate(data, filters) {
    filters = normalizeFilters(filters, data.categories);
    var projects = filterProjects(data.projects, filters);
    var stars = starConcentration(projects);
    return {
      sharedNames: sharedNames(projects),
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
      push: dateHistogram(projects, 'pushed_at', data.metrics_as_of, RECENCY_BOUNDS, RECENCY_LABELS),
      release: dateHistogram(projects, 'release_at', data.metrics_as_of, RECENCY_BOUNDS, RECENCY_LABELS),
      concentration: stars
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

  function formatNumber(value) {
    return new Intl.NumberFormat('en-US').format(value);
  }

  function svgElement(doc, name, attributes, text) {
    var element = doc.createElementNS(SVG_NS, name);
    Object.keys(attributes || {}).forEach(function (key) { element.setAttribute(key, attributes[key]); });
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function renderChart(doc, container, rows, valueLabel) {
    if (!container) return;
    var tbody = container.querySelector('tbody');
    var svg = container.querySelector('svg');
    var max = rows.reduce(function (value, row) { return Math.max(value, row.count); }, 0);
    if (tbody) {
      var fragment = doc.createDocumentFragment();
      rows.forEach(function (row) {
        var tr = doc.createElement('tr');
        tr.setAttribute('data-key', row.id || row.label);
        tr.setAttribute('data-count', row.count);
        var label = doc.createElement('th');
        label.setAttribute('scope', 'row');
        label.textContent = row.label;
        var count = doc.createElement('td');
        count.textContent = formatNumber(row.count);
        count.style.setProperty('--bar-fraction', max ? (row.count / max * 100) + '%' : '0%');
        tr.appendChild(label);
        tr.appendChild(count);
        fragment.appendChild(tr);
      });
      if (!rows.length) {
        var empty = doc.createElement('tr');
        var cell = doc.createElement('td');
        cell.colSpan = 2;
        cell.textContent = 'No observed values in this selection.';
        empty.appendChild(cell);
        fragment.appendChild(empty);
      }
      tbody.replaceChildren(fragment);
    }
    if (!svg) return;
    var width = 640;
    var labelWidth = 240;
    var plotWidth = 330;
    var rowHeight = 32;
    var top = 36;
    var height = Math.max(80, top + rows.length * rowHeight + 8);
    svg.setAttribute('viewBox', '0 0 ' + width + ' ' + height);
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    svg.replaceChildren();
    svg.appendChild(svgElement(doc, 'text', { x: labelWidth, y: 14, 'class': 'chart-scale' }, '0'));
    svg.appendChild(svgElement(doc, 'text', { x: labelWidth + plotWidth, y: 14, 'text-anchor': 'end', 'class': 'chart-scale' }, formatNumber(max) + ' ' + (valueLabel || 'projects')));
    for (var tick = 0; tick <= 4; tick += 1) {
      var x = labelWidth + plotWidth * tick / 4;
      svg.appendChild(svgElement(doc, 'line', { x1: x, y1: 24, x2: x, y2: height - 10, 'class': tick === 0 ? 'chart-zero' : 'chart-gridline' }));
    }
    rows.forEach(function (row, index) {
      var y = top + index * rowHeight;
      var label = row.label.length > 29 ? row.label.slice(0, 28) + '…' : row.label;
      svg.appendChild(svgElement(doc, 'text', { x: 0, y: y + 11, 'class': 'chart-label' }, label));
      svg.appendChild(svgElement(doc, 'rect', { x: labelWidth, y: y, width: max ? row.count / max * plotWidth : 0, height: 15, 'data-key': row.id || row.label, 'data-count': row.count, 'class': row.label === 'Unknown' ? 'chart-bar chart-bar-unknown' : 'chart-bar' }));
      svg.appendChild(svgElement(doc, 'text', { x: width, y: y + 11, 'text-anchor': 'end', 'class': 'chart-count' }, formatNumber(row.count)));
    });
    if (!rows.length) svg.appendChild(svgElement(doc, 'text', { x: 0, y: 53, 'class': 'chart-label' }, 'No observed values in this selection.'));
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
    var summary = doc.getElementById('selection-summary');
    var download = doc.getElementById('export-csv');
    var objectURL = null;
    var projectRows = Array.from(doc.querySelectorAll('#project-table tbody tr[data-id]'));
    var projectBody = doc.querySelector('#project-table tbody');
    var emptyRow = doc.getElementById('project-table-empty');
    if (projectBody && !emptyRow) {
      emptyRow = doc.createElement('tr');
      emptyRow.id = 'project-table-empty';
      emptyRow.hidden = true;
      var emptyCell = doc.createElement('td');
      emptyCell.colSpan = doc.querySelectorAll('#project-table thead th').length || 8;
      emptyCell.textContent = 'No projects match these filters.';
      emptyRow.appendChild(emptyCell);
      projectBody.appendChild(emptyRow);
    }

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
      if (updateLocation) setLocation(result.filters, replace);
      doc.querySelectorAll('[data-metric]').forEach(function (element) {
        var key = element.getAttribute('data-metric');
        if (Object.prototype.hasOwnProperty.call(result.metrics, key)) element.textContent = formatNumber(result.metrics[key]);
      });
      var names = data.categories.filter(function (item) { return item.id === result.filters.category; });
      if (summary) {
        var selection = names.length ? names[0].name : 'all categories';
        var licenseSelection = result.filters.license === 'all' ? 'all license observations' : result.filters.license === 'known' ? 'known license' : 'unknown license';
        summary.textContent = formatNumber(result.metrics.total) + ' of ' + formatNumber(data.projects.length) + ' projects · ' + selection + ' · ' + licenseSelection + '.';
      }
      if (reset) reset.disabled = result.filters.category === 'all' && result.filters.license === 'all';
      doc.getElementById('shared-name-count').textContent = formatNumber(result.sharedNames.tool_count);
      doc.getElementById('exact-name-count').textContent = formatNumber(result.sharedNames.exact_tool_count);
      doc.getElementById('whitespace-name-count').textContent = formatNumber(result.sharedNames.whitespace_tool_count);
      doc.getElementById('capitalization-name-count').textContent = formatNumber(result.sharedNames.capitalization_tool_count);
      renderNameGroups(doc, doc.getElementById('exact-name-groups'), result.sharedNames.exact);
      renderNameGroups(doc, doc.getElementById('capitalization-name-groups'), result.sharedNames.capitalization);
      renderNameGroups(doc, doc.getElementById('whitespace-name-groups'), result.sharedNames.whitespace);
      renderChart(doc, doc.getElementById('category-chart'), result.categories);
      renderChart(doc, doc.getElementById('license-chart'), result.licenses);
      renderChart(doc, doc.getElementById('age-chart'), result.age);
      renderChart(doc, doc.getElementById('push-chart'), result.push);
      renderChart(doc, doc.getElementById('release-chart'), result.release);
      renderChart(doc, doc.getElementById('star-chart'), result.concentration.rows, 'stars');
      var concentration = doc.getElementById('star-concentration-summary');
      if (concentration) concentration.textContent = result.concentration.share === null ? 'No observed stars in this selection.' : 'The ' + result.concentration.topCount + ' largest observed counts total ' + formatNumber(result.concentration.topTotal) + ' stars (' + (result.concentration.share * 100).toFixed(1) + '% of observed stars in this selection).';
      var visible = new Set(result.projects.map(function (project) { return project.id; }));
      projectRows.forEach(function (row) { row.hidden = !visible.has(row.getAttribute('data-id')); });
      var empty = doc.getElementById('project-table-empty');
      if (empty) empty.hidden = result.projects.length !== 0;
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
    CSV_COLUMNS: CSV_COLUMNS, knownLicense: knownLicense, knownStars: knownStars,
    normalizeFilters: normalizeFilters, readFilters: readFilters, filterSearch: filterSearch,
    filterProjects: filterProjects, isoDay: isoDay, dateHistogram: dateHistogram,
    categoryCounts: categoryCounts, licenseCounts: licenseCounts, starConcentration: starConcentration,
    sharedNames: sharedNames, aggregate: aggregate, csvCell: csvCell, exportCSV: exportCSV, renderChart: renderChart, init: init
  };
}));
