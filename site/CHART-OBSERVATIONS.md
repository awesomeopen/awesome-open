# Collected chart observations

`data/chart_observations.json` is a versioned, append/deduplicate archive of
completed HN and aggregate GitHub-star observations. The existing
`hn_evidence.json` and `star_history.json` caches still supply the same last
24 completed months to the renderer. The archive does not change charts,
counts, eligibility, collection budgets, endpoints or schedules. It does not
add a range selector.

## Meaning and dates

Each observation retains one completed collection's identity, window, counts,
source URLs and raw evidence. HN includes accepted and excluded stories,
matching reasons, reviewed identity fields and the original identity fingerprint
when one existed. A later identity-map revision is another observation, not a
rewrite of previous inclusion decisions. Catalog removal does not remove archived
evidence, and missing history never creates zeros.

GitHub observations retain all fetched weekly/day bins, including any bins
outside the chart window, coverage proof, source revision and original
`fetched_at`. These measure stars created in a month that remained at that fetch.
Unstars and upstream corrections can change old buckets at a later fetch. Both
observations remain separate; do not sum them or splice buckets into historical
total stars or gross stars received. Source daily-bin month boundaries remain
approximate, as documented by the current collector.

HN's `collected_at` is preserved when available. Legacy schema-1 evidence records
its original `refreshed_utc_date` at day precision. Migrated queue payloads without
a collection date keep `observed_at: null`. A later attempt, Git commit date,
recovery time or build date is never substituted for an unknown collection date.
The archive can therefore contain an undated migrated payload and its earlier
dated legacy representation. Their raw evidence is deduplicated without claiming
that the missing timestamp was recovered.

## Schema 1

- `observations`: SHA-256 keyed immutable observations. Each has `kind`, canonical
  `identity`, an `evidence` reference, original date/source-revision `metadata`,
  and `observed_at` (value, precision and original field, or null).
- `objects`: SHA-256 keyed typed evidence. Individual HN story records and
  GitHub weekly bins are stored once by content. Evidence bundles reference
  these objects. Changed title/matching decisions or star bins create new
  objects; unchanged raw data is reused across fetches and window changes.
- `recoveries`: SHA-256 keyed local-Git recovery manifests. Each records an exact
  base SHA, bounded first-parent scan, source commit/blob/path and newly recovered
  observation references. Skipped invalid snapshots and truncation are explicit.

Hashes use canonical UTF-8 JSON with sorted keys and compact separators. The file
uses one line per object/observation to keep diffs reviewable. Identical repeated
cache reads produce no new observations or writes. A genuinely new completed
fetch retains its date even if counts are unchanged; it reuses unchanged evidence.
The archive grows with distinct observations and evidence, not each daily build's
copy of every raw cache. There is no eviction policy for collected observations.

`chart_observations.materialize()` reconstructs the completed payload exactly.
Validation checks hashes, typed references, source identities, dates, complete
windows, original HN identity fingerprints and the existing evidence validators.
The archive contains untrusted source text as data; nothing in it is executed.
Offline build output does not embed the full archive.

## Collection and publication

The collector CLI archives the existing cache before collection/removal, then
atomically saves each newly completed observation before replacing `last_good`.
Incomplete or failed attempts do not become complete observations. Existing HN
partial-page checkpoint/resumption rules are unchanged; these working pages are
not a permanent completed-observation history. A local archive error stops the
collector rather than becoming an ordinary optional-upstream failure.

The normal publisher permits only the exact archive path in addition to its
existing generated allowlist. A disposable attempt's archive is carried forward
across fresh-main retries and unioned with the latest main archive. Current cache
and curated source still regenerate from fresh main. A failed/stale attempt cannot
erase already collected successful observations merely because the invocation's
request budget prevents querying them again. Cached publication also archives
its current snapshots without API calls.

The bounded backfill archives both the previous cache and every validated incoming
complete record before selecting eligible/newer records for the live cache. A
result collected before a concurrent catalog removal, or an older result beaten
by a newer fetch on main, is retained as an observation without replacing the
live cache. Backfill checkpoints commit the archive and cache together, after the
full offline suite. Both publication paths re-fetch main and use ordinary
fast-forward pushes. The existing serialized publisher remains the single writer;
independent concurrent manual collector processes are not an additional supported
writing service.

Atomic local files are not a guarantee that an unpublished job survives runner
loss. Successful Git commits are the durable remote boundary. The normal
publisher writes its carry archive to `tmp/chart-observations/archive.json`
before disposing each attempt, including terminal failures. Failed or cancelled
workflows upload that exact recovery file for 14 days when Actions cleanup can
run. A hard job termination before checkpoint/upload can still lose uncommitted
observations. The bounded
backfill still saves its existing per-repository recovery artifact, subject to
Actions cleanup availability and its existing retention period. Recovery files are not automatically imported from Actions: validate them and
union their observations with fresh main before a reviewed recovery publication.
No credentials, workflow permissions or background schedule are introduced.

## Initial recovery

The seed was recovered offline from first-parent history through
`bde34ad7ac4740124e9e9279f2e902d19fab34df`, with a ceiling of 200 snapshot-changing
commits: 56 commits and 59 unique cache blobs were scanned, with no invalid
snapshots skipped and no truncation.

- HN: 131 observations across 115 canonical identities. There are 16 legacy
  day-precision observations from October 3, 2026, 100 timestamped collections
  from October 15–16, and 15 undated migrated payloads.
- GitHub: 187 observations across 187 repositories, preserving fetch dates
  October 13, October 15 and October 16, 2026.
- Complete chart-window coverage is October 2024 through September 2026. No
  older complete chart window was found. All raw fetched bins and story evidence
  are retained as originally stored; no additional historical API crawl ran.

Reproduce the bounded recovery from local Git objects:

```sh
python3 scripts/recover_chart_observations.py --ref origin/main --max-commits 200
python3 -m unittest discover -s scripts -p 'test_*.py'
```

Recovery does not fetch Git or call upstream APIs. The command prints exact
coverage and any truncated/skipped history. A source commit in its manifest
establishes where evidence was recovered, not when the provider was queried.

## Display-name-only changes

The original HN identity hash and observation payload stay immutable. Current
queue reuse can verify that original hash and compare all identity fields except
the display name; matching/query changes still invalidate reuse. See the
[alias and rename contract](PROJECT-ALIASES.md). Current chart labels may use the
new catalog name without rewriting archived names, collection dates or hashes.
