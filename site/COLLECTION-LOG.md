# Collection log

The moss block between HN evidence and Scorecard shows recent dated activity
retained for the project. Its `i` opens an oldest-first overview with provenance.

The build derives up to four records from completed HN/star observations,
metadata attempts and successes, Function review dates and name-change review
dates. Unknown collection dates are omitted. Rename occurrence dates stay in the
name-change timeline; they never stand in for evidence collection. Review dates
say “reviewed”, not “added”. No age or activity-level judgment is displayed.

Version 1 records contain `at`, `precision`, `kind`, `label` and `source`.
They are deterministic, deduplicated and bounded before rendering. The archive
is read once during the offline build; only record HTML carries the event list.
Neither the initial index, catalog JSON nor search-text download carries it.
The retained overview is a subset of available evidence, not a complete audit
since catalog inclusion. A future journal may supply additional event kinds.

Three small monospaced lines replay the dated sequence every six seconds while
visible. Hover, keyboard focus, an open disclosure, a closed plate or hidden tab
pauses it. Reduced motion keeps the static recent lines. Zero or one record stays
static. The replay is hidden from assistive technology; the native disclosure
provides the readable list without live announcements. Removed plates release
their timer and visibility observer.

Validation covers derivation, date precision, omitted unknown dates, payload
bounds, compact-index exclusion, mobile disclosure, replay and reduced motion.
