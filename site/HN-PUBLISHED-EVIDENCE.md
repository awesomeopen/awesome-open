# Published HN evidence

The site's `data/hn_evidence.json` uses schema 3 to store identical recovery
project copies once. Every story, excluded candidate, query, count, date, queue
checkpoint and recovery field remains reconstructible. The collector's tracked
`data/hn_evidence.json` keeps its existing schema and contents.

## Reading schema 3

`projects` retains the complete current project objects in their original order.
For each `queue[url].last_good`, an integer `project_ref` replaces `project` only
when that entire object equals the current project for the same canonical URL.
The integer is a zero-based index into `projects`. A distinct last-good snapshot
keeps its complete inline `project`. Null or absent last-good results remain so.
All other fields retain their values. `source_schema_version` records the
collector version (1 or 2); `schema_version` is 3 in this download.

Use `published_hn.materialize(document)` from `scripts/` to reconstruct the
collector document. It returns independent objects, restores the source version,
and removes the export-only version field. It also accepts legacy schema-1/2
downloads. Unsupported versions, duplicate current identities, noninteger,
out-of-range or identity-mismatched references, and simultaneous inline/reference
values fail with `ValueError`. References apply only at `last_good.project_ref`;
story contents and other nested fields are never interpreted as references.
The decoder validates the representation; collector evidence validation remains
owned by the existing HN validators.

The current website reads catalog summaries and generated record HTML. Its HN
charts are built from the source snapshot before this export step. Existing
consumers of the download's `projects` array retain the same content. Consumers
of recovery queue objects must decode schema 3 before expecting inline projects;
collector imports must use the reconstructed source document. Reconstruction
preserves JSON values and array order, rather than source whitespace or key order.

## Size and the 1,000-project plan

Measured against main `0478c7e9cc13045e64648c99894aaa8c73922542` on
13 November 2026, using UTF-8 compact JSON plus one newline:

| Measure | Bytes |
| --- | ---: |
| Previous published download, 584 projects | 6,566,932 |
| Schema 3 download, 584 identical recovery copies referenced | 3,512,188 |
| Saved | 3,054,744 |
| Current largest-other-file budget (584 × 8,192) | 4,784,128 |
| Linear schema-3 estimate at 1,000 projects | 6,014,021 |
| Existing budget at 1,000 projects | 8,192,000 |

The existing budget is retained. The estimate leaves about 2.18 MB for variation
at the planned roughly 1,000 curated projects, followed by pruning. It assumes
the current average story volume, metadata size and identical-recovery share.
Project sizes are skewed: the current median is 1,123 bytes and the largest is
1,035,016 bytes (including the per-object newline). A few heavily discussed
additions can outweigh hundreds of small projects.

Distinct recovery snapshots and partial pages remain inline and can exceed this
estimate. Scaling today's fully duplicated payload to 1,000 gives approximately
11,244,747 bytes; similarly sized but distinct recovery snapshots could approach
that amount and exceed the budget. Catalog pruning also need not immediately
remove retained queue entries. These are scenarios, not maximum sizes: future
story volume and checkpoint growth are unbounded by the project count. Review
actual built bytes as the catalog approaches its target. This representation
preserves evidence when a budget fails; it never truncates stories to pass.

The budget measures uncompressed output bytes. Transfer compression, browser
memory and the independently retained observation archive have separate sizes.
The archive is excluded from site output.

Reproduce the download measurement from the repository root:

```sh
PYTHONPATH=scripts python3 - <<'PY'
import json
from pathlib import Path
from build_site import compact_json
from published_hn import publish, materialize
source = json.loads(Path('data/hn_evidence.json').read_text())
published = publish(source)
assert materialize(published) == source
for name, value in [('source', source), ('published', published)]:
    print(name, len(compact_json(value).encode('utf-8')))
PY
python3 scripts/check_budget.py tmp/site
```
