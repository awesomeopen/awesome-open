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

## Multi-year capacity plan (November 21, 2026)

The HN-only allowance is **96 KiB per catalog record**: 57,704,448 bytes
at 587 records and 98,304,000 at 1,000. The owner requested room for roughly
1,000 entries with multiple years of HN evidence. This changes only the size
guard, preserving the export and every collected field.

Run `python3 scripts/plan_hn_capacity.py` to reproduce the model from checked-in
caches. At source `a23bf4c3e4c61b774ab194ad33248d941cf60c7f`, the export is
6,265,190 bytes before and after this policy change. The former 10 KiB allowance
was 6,010,880 bytes. New current headroom is 51,439,258 bytes.

The actual published window is November 2024 through October 2026 (24 complete
months). It retains matched stories, broad title/URL search candidates including
excluded candidates, dates, monthly bins, identity/query provenance, and queue
checkpoints. Broad and matched lists can overlap; this model measures their
actual bytes rather than assuming story-level deduplication. All 587 identical
last-good recovery objects currently use references. Distinct recovery snapshots
and partial pages remain inline. The separate immutable observation archive
retains older collections and is not embedded in this download. Years below
model longer represented windows; they do not enable a new retention policy or
claim that the rolling export accumulates a full new copy every year.

Of 587 cached projects, 257 contain matched/broad/excluded story evidence and
330 have none. Their mean object sizes are 20,315 and 1,837 bytes respectively.
The richer cohort median is 4,535 bytes; its largest object is 1,035,016 bytes.
Using today's overall average would conceal both sparse coverage and skew.

The model fills all 1,000 slots from the richer cohort, retaining its observed
skew. It separates mean fixed query/identity overhead (2,249 bytes), history
fields (18,066 bytes per two years), and global/queue overhead (746 bytes per
project). History fields scale with represented years. A second scenario adds
25% distinct full recovery copies and five extra largest-project equivalents,
scaled with years. These are explicit planning assumptions, not forecasts of
upstream traffic or a worst-case bound.

| Represented years | Richer full coverage | Plus recovery and extra skew |
| --- | ---: | ---: |
| 2 | 21,060,908 B | 31,314,628 B |
| 5 | 48,159,774 B | 72,950,831 B |
| 10 (stress case) | 93,324,550 B | 142,344,501 B |

96 KiB/project rounds above the five-year recovery/skew scenario with
25,353,169 bytes (35%) planning margin at 1,000 projects. The ten-year stress
case with extra recovery exceeds it and would trigger another measured review.
No finite project-count cap guarantees capacity for unlimited stories, partial
results or query growth. Review this estimate after major coverage/query changes.

These are uncompressed artifact bytes. The evidence download is linked on demand;
charts and ordinary browsing use generated records/catalog rather than parsing
this whole file. Compression reduces transfer, but clients that download and
parse the full JSON can need substantially more memory than its byte size.
No device-memory benchmark is implied. Existing total-site and non-artwork guards
remain independent: a future 73 MB HN file can require a separate overall
capacity review even though it fits this HN guard.

The strict site-budget check runs immediately after the production build, including
its published hero, and before exhibition and jar previews add their review-only
output. The overall allowance stays at 20 MiB + 58 KiB/project. At this baseline,
production uses 54,665,177 of 55,834,624 non-artwork bytes, leaving 1,169,447 bytes.
Adding both previews produces 56,435,455 bytes; those duplicate review pages are
outside the production accounting. Both preview builds and all browser checks
remain required. This separates intentional preview output from shipped capacity;
production growth still fails the same strict guard. See [preview validation](PREVIEW.md#production-budget-and-preview-validation).
Held data proposals still require their own complete validation.

## Historical November 15 size baseline

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
