# Scoreboard

`/scoreboard/` displays six Top 10 rankings from cached evidence. Places 1–3 carry
small numbered trophies, repeated as links on each current specimen plate.
Each trophy names its metric and the current snapshot's update date. The page
shows one current set of tables, with optional **Over time** views beneath them.

## Measurements

| Board | Measurement | Qualifying evidence |
| --- | --- | --- |
| Oldest repository | UTC days from GitHub repository creation to the frozen metrics date | Known creation date at or before that date |
| Longest release-to-push gap | Positive UTC calendar-day difference: last repository push minus latest full GitHub release publication | Both dates, with push after publication |
| Most recorded software renames | Distinct reviewed `software_rename` events | Projects with recorded software renames |
| Longest matched HN story-day streak | Longest consecutive run of UTC dates with a matched story | Completed current-window collection with stories |
| Most matched HN stories | Distinct matched story IDs | Completed current-window collection with stories |
| Most cached GitHub stars | Observed star count | Known count, including observed zero |

The release date is `published_at` from GitHub's latest published full release;
pre-releases, drafts and other release channels remain outside that signal.
A same-day or negative release-to-push gap is excluded. Repository age refers to
repository creation. Rename coverage is the reviewed ledger, not a complete
historical census; repository path changes and owner transfers stay separate.

HN uses the cache's 24 completed UTC months, with its exact start-inclusive and
end-exclusive boundaries printed on the page. Distinct stories on one day count
as one streak day. Equal longest runs keep the earliest start. Matching scope
varies: most projects match only their catalog URL; broader title/domain scopes
require reviewed identity evidence. Algolia coverage is best-effort. Incomplete
queue pages and the historical `eligible` threshold never determine ranking.
Retained complete observations keep their actual collection date and latest
attempt status. Legacy observations without a collection timestamp say so.

Each board states its qualifying count. Unknown values are excluded. Retained
GitHub/release values retain their stale status and observation dates in row
evidence. The snapshot download keeps frozen values and provenance.

## Weekly publication

Weeks are Monday–Sunday in `America/New_York`, matching Spotlight's calendar.
The first successful **normal** publisher run in a week freezes that week's
Scoreboard from its validated caches. It displays immediately; Spotlight's
one-week-ahead draw policy remains unchanged. The weekly snapshot records cached measurements as of their stated source dates.

`scripts/weekly_scoreboard.py` runs offline in the existing serialized publisher,
after collection and before validation. `data/weekly_scoreboard.json` is the
publisher-owned current snapshot and measurement history. It records the week, actual recording date,
metrics date, HN window, source SHA, input SHA-256 fingerprints, qualifying counts,
and ranked rows. Same-week reruns preserve it byte-for-byte. The existing
publisher validates before committing, fetches main again before pushing, and
restarts on concurrent changes; unpublished attempts never become editions.
Collection, credentials, schedules and workflow permissions remain unchanged.

The page leads with **Updated YYYY-MM-DD**, using the actual snapshot recording
date. Weekly boundaries remain a publisher rule rather than an archive of reader
pages. Cached repair publication and ordinary offline builds preserve the saved
snapshot. Before first publication, the page states that no snapshot exists and
plates have no trophies.

## Measurement history

Schema 2 keeps compact, dated observations of every qualifying project alongside
the current Top 10 in the same atomic snapshot file. Stable project identities
and shared source facts are stored once; measurements reference that evidence.
`history_projects` is an append-stable list of full canonical ID, name and URL.
`history_details` holds digest-verified `facts` and `provenance` objects; each
measurement stores project index, value, fact index and provenance index.
`history_view()` resolves those references for rendering and validation. Each weekly observation
retains its source revision, input fingerprints, catalog and qualifying counts,
measurement date and HN window. The existing publisher commits the file only
after validation. Same-week reruns preserve its bytes; missing weeks add no
observations. The existing collection schedule remains unchanged.

Schema 1 remains readable. Its recorded Top 10 can appear as a **top-10-only**
observation; projects outside those rows have no saved value. At the next weekly
freeze, schema 2 preserves that exact partial observation and starts all-eligible
history. It does not reconstruct earlier standings or fill absent values with
zero. Names can follow the latest known label for a canonical identity; saved
Top 10 rows keep their frozen names.

**Over time** opens beneath each board. Up to three current leaders have native
project disclosures, readable without JavaScript. Observed-value charts default
to a 12-month range with monthly labels and retain actual observation dates.
A single observation is a point, not a fabricated trend. Missing measurements
remain gaps. The latest actual capture in each month supplies the plotted point;
its exact date remains visible. Source links, dates and values are available as
text alongside the chart. The page embeds only its selected series; the full
archive is an explicit download. Captured observations are retained without
an automatic expiry.

| Measurement | Historical view |
| --- | --- |
| Repository age | Repository creation-date comparison |
| Release-to-push gap | Observed gaps with evidenced release-publication dates |
| Recorded software renames | Verified occurrence timeline, with separately labeled record/review dates when known |
| HN story-day streak | The evidenced start and end of the selected streak |
| Matched HN stories | Monthly submission counts from a saved complete-window observation, when available |
| Cached GitHub stars | Observed total stars at their recorded cache timestamps |

Historical HN bars describe story dates within the stated matching window, not
past Scoreboard standings. Legacy snapshots without monthly counts state that
limit until an actual capture supplies them. Retained-star acquisition buckets
are a different measurement and do not supply total-star history.

Changing catalog membership, matching scope, collection coverage or reviewed
rename evidence can change a ranking. The method exposes those limits and the
qualifying counts; charts describe measurements rather than historical places.
Only the current tables award plate trophies.

Removed projects remain in their frozen board with saved names and official-source
links. Only matching current canonical IDs receive plate trophies. Current names
may differ from a frozen table's saved name until the next weekly edition.

## Places and ties

Use competition ranking: `1, 1, 3`. Equal measured values share a place. Canonical
Registry ID provides stable ordering within ties. Include every project whose
place is at most 10; ties at the cutoff can produce more than ten rows. Shared
places 1–3 receive the same numbered trophy. A board with fewer qualifying
projects shows only those projects. No combined score is calculated.

## Build and review

Normal site builds read the saved snapshot without network access or wall-clock
ranking. An explicit provisional preview is available for implementation review:

```sh
python3 scripts/build_site.py --output tmp/scoreboard-preview --scoreboard-preview
```

This option computes from cached evidence in memory, labels the page and trophies
as provisional, and writes no weekly cache. It cannot be combined with
`--production`. Normal production output never silently computes a replacement
when its snapshot is absent.

Run the full offline suite, brand check, README preview, catalog/site builds and
browser suites. `scripts/check_scoreboard_browser.cjs` verifies the explicit
preview, all six tables, competition ranks, trophy links, history, narrow layout,
keyboard access and no-JavaScript evidence disclosures. Its screenshots and report
are retained with the other CI preview artifacts.

The page extends the Observatory route shell: white/Prussian frame, serif headings,
ruled comparative tables, visible section links, native evidence disclosures and
shared footer. The small `rank.trophy` glyph is a code-authored interface icon;
existing specimen artwork is unchanged.


## Compact presentation

Each ranking entry occupies one line: place, project name and linked count.
Long project names truncate with an ellipsis and retain the full name in a title.
The count opens the native evidence disclosure as an overlay, styled as a plain
underlined link with no marker. Units appear in column headers. Retained-cache
status appears inside evidence. Keyboard and no-JavaScript access are preserved.

Display titles use “Most names”, “Longes HN streak”, “Most HN stories” and
“Most GitHub stars”. Frozen snapshots retain their recorded titles and values;
the renderer applies current presentation labels. The page ends after the
rankings, optional trends and their methods, followed by the shared footer and
snapshot download.
