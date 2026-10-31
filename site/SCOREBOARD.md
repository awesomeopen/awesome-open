# Scoreboard

`/scoreboard/` displays six Top 10 rankings from cached evidence. Places 1–3 carry
small numbered trophies, repeated as links on each current specimen plate.
Each trophy names its metric and edition.

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
one-week-ahead draw policy remains unchanged. These are weekly editions of
cached measurements, not measurements of performance during the preceding week.

`scripts/weekly_scoreboard.py` runs offline in the existing serialized publisher,
after collection and before validation. `data/weekly_scoreboard.json` is the
publisher-owned latest snapshot. It records the week, actual recording date,
metrics date, HN window, source SHA, input SHA-256 fingerprints, qualifying counts,
and ranked rows. Same-week reruns preserve it byte-for-byte. The existing
publisher validates before committing, fetches main again before pushing, and
restarts on concurrent changes; unpublished attempts never become editions.
No collector, credential, schedule or workflow permission is added.

Only the latest edition is retained in this cache; Git history retains previously
published editions. Missed weeks are not reconstructed. Cached repair publication
and ordinary offline builds retain the edition without advancing it. A delayed
weekly publication keeps the original week and dates visible. Before the first
normal publication, the page states that no edition exists and plates have no
trophies.

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
rankings and their methods, followed by the shared footer and snapshot download.
