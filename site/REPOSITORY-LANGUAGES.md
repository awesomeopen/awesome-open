# Repository languages

Repository languages are GitHub's detected source composition, measured in bytes.
The plate shows the three leading names; its disclosure gives every language,
byte count, percentage, source URL, checked time and last successful fetch.
The language filter matches any detected language, including a retained stale
observation. Search includes the same names, preserving punctuation such as C++
and C#.

Unknown means no successful breakdown is cached. “None detected” means GitHub
successfully returned an empty object. A failed refresh retains the last-good
breakdown and marks it stale; a deferred check retains its previous dates.
Non-GitHub projects remain unknown. GitHub's primary-language metadata is saved
by the existing metrics request and may appear in the disclosure while the full
breakdown is missing; it does not stand in for an observed full breakdown.
Runtime requirements and supported APIs need their own evidence.

## Collection

The existing serialized publisher owns `data/project_signals.json`. Its optional
languages provider requests `/repos/{owner}/{repo}/languages`, with a ceiling of
30 requests per run within the existing 300-second optional-provider deadline.
Successful observations are due after seven days and become stale after fourteen
days without successful revalidation. Failed checks become due after one day;
Retry-After and GitHub quota backoff take precedence. Least-recently-attempted
rotation fills missing records over successive publisher runs. Refreshes are
best-effort within the shared deadline. Initial coverage takes multiple runs,
and deferred observations may become stale. ETags allow 304
revalidation without changing the original value-fetch date.

GitHub release and language requests share rate-limit backoff. Redirects are
refused and retain stale evidence for identity review. Optional transport/provider
outages preserve core publication; malformed local records, invalid provider
schemas and source identity mismatches still fail closed. Existing metrics
repository-ID checks remain in force. Legacy two-provider snapshots are validated
before the collector adds the language provider. No new schedule, credentials or
candidate-software execution is introduced.

## Views

The language box uses the former reserved space between Release record and Where
it runs. It uses the existing white evidence-box treatment and native information
disclosure, including on narrow screens and static records. The other reserved
block remains decorative.

Catalog JSON retains byte counts, status and provenance; repeated null optional
metadata is omitted. Language ETags, retry delays and HTTP status live in the
collector download; availability and failure reasons stay in the catalog.
A language observation uses its identical `fetched_at`
time in place of a duplicate `observed_at`. The evidence download retains the
complete collector schema. The embedded search index keeps the names
and availability status. `language` URL state, reset and history use the shared
Catalog predicates. `unknown` and `empty` select distinct evidence states.
WebMCPlet exposes a searchable, filterable `languages` list and cache status.
Cabinet find accepts an exact `language` filter; inspect and compare return the
language evidence with source, dates and byte counts. The visible comparison
shows the names, byte counts, check date and cache status.

Reference: [GitHub REST repository languages](https://docs.github.com/en/rest/repos/repos#list-repository-languages).

Contribution by Junge (AI)
