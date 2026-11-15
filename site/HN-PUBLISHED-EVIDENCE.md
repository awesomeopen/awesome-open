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

Measured against main `f4cb6046c138914a78719808c6a7c874b784a98a` on
15 November 2026, using UTF-8 compact JSON plus one newline:

| Measure | Bytes |
| --- | ---: |
| Previous published download, 584 projects | 9,321,484 |
| Schema 3 download, 584 identical recovery copies referenced | 4,887,935 |
| Saved | 4,433,549 |
| Previous largest-other-file budget (584 × 8,192) | 4,784,128 |
| New HN-only budget (584 × 10,240) | 5,980,160 |
| Linear schema-3 estimate at 1,000 projects | 8,369,752 |
| New HN-only budget at 1,000 projects | 10,240,000 |

Compaction alone exceeds the previous current-catalog limit by 103,807 bytes.
HN now has a separate 10 KiB-per-record budget, about 22% above the current
compact average, with 1,092,225 bytes of headroom at 584 records. Other files
keep their existing limits. At the planned roughly 1,000 curated projects,
followed by pruning, the same average leaves about 1.87 MB of headroom.

The earlier 13 November measurement was 6,566,932 raw / 3,512,188 compact bytes.
Its 8,192,000-byte figure was the old budget at **1,000 projects**;
the old budget for the current **584 projects** was 4,784,128 bytes. Evidence
growth since that measurement consumed the earlier headroom without adding
projects. The refreshed estimate assumes today's story volume, metadata size
and identical-recovery share. Project sizes are skewed: the median is 1,153
bytes and the largest is 1,035,016 bytes (including the per-object newline).
A few heavily discussed additions can outweigh hundreds of small projects.

Distinct recovery snapshots and partial pages remain inline and can exceed this
estimate. Scaling today's fully duplicated payload to 1,000 gives approximately
15,961,445 bytes; similarly sized but distinct recovery snapshots could approach
that amount and exceed the new budget. Catalog pruning also need not immediately
remove retained queue entries. These are scenarios, not maximum sizes: future
story volume and checkpoint growth are unbounded by project count. Review actual
built bytes as the catalog approaches its target and after large refreshes.
This representation preserves evidence when a budget fails; it never truncates
stories to pass.

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
