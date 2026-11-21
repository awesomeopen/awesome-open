# Collection log

The collection block replays four recent recorded activities. Click anywhere in
the block, or focus it and press Enter or Space, to open the retained chronology
with source links and dates, newest first. Equal dates retain their source order;
undated observations follow dated entries.
There is no event-count cutoff in the overview.

Completed HN/star observations keep their collection dates and archive references.
Undated archived observations are counted separately. Metadata supplies its latest
attempt and success; optional release, language and Scorecard evidence supplies
retained attempt, successful check and payload-fetch dates. These are distinct
operations, even when their timestamps coincide.

Function, feature, alias, deployment, alternative and name-change records supply
explicit review dates. Approved specimen artwork supplies its creation date.
Feature notes without a separate review date get no invented event. Rename and
release occurrence dates, repository creation, and build time never stand in for
collection time. No age or activity-level judgment is displayed.

This covers the retained dated fields above, including older chart observations.
The inclusion date and overwritten metadata/review history are unavailable here;
this is not a complete journal since inclusion. Weekly ranking/draw dates describe
editorial selections, not evidence collection, and are outside this chronology.

## Delivery and replay

The offline build writes one compact `collection/<id>.json` per project. Version
1 interns each type's kind, label and source in `types`; each `events` row contains
its date, type index and optional archive observation ID. `undated` holds counts
by chart type. Dates retain day/second precision. Every distinct archived
observation survives, including observations at the same timestamp. Other exact
duplicates of the same date, kind and source are coalesced.

Only four short date/label pairs travel in record HTML. Neither the initial index,
catalog JSON nor search-text download carries the chronology. Opening the block fetches
the project's JSON once; repeated opens reuse it. A failed fetch can be retried by
reopening. The full list uses a scrollable native modal with a named title and
Close control. Escape closes it and returns focus to the block. The underlying
JSON remains available at its existing path.

Three small monospaced lines replay every six seconds while visible. Hover,
keyboard focus, an open modal, closed plate or hidden tab pauses replay.
Reduced motion keeps the static recent lines. Zero or one event stays static.
Removed plates release their timer and visibility observer.

## Capacity review

The owner requested an overview of retained evidence beyond the recent replay.
The previous four-event disclosure omitted older retained evidence. The correction
keeps chronology outside record HTML, interns repeated labels/source URLs within
each file, and adds no upstream requests or stored copies of raw provider data.

On the same 587-project baseline, production plus exhibition/jar previews measured
54,532,189 non-artwork bytes before this correction. The correction measures 55,494,581 bytes, including 1,181,764 bytes in 587 lazy
chronology files. It contains 7,298 dated records and 15 undated chart observations;
542 projects have more than four dated records. The allowance
changes from 20 MiB + 56 KiB/project (54,632,448 bytes) to 20 MiB + 58 KiB/project
(55,834,624 bytes), leaving 340,043 bytes of margin. At 1,000 projects it changes from 78,315,520 to 80,363,520 bytes.
All other limits remain in force. Future growth still requires measured review;
no event eviction is used to make a budget pass.

Only the opened project's file is transferred and parsed: current files average
about 2 KiB and peak around 3.2 KiB before compression. DOM rows are created only
on disclosure. These byte measurements support the small incremental cost; they
are not low-end-device memory or latency benchmarks.

Tests cover older evidence, unknown dates, provenance, payload/index separation,
lazy loading, repeated opening, mobile disclosure, replay and reduced motion.
