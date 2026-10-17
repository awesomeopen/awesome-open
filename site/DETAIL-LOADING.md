# On-demand specimen details

Draft implementation contract. The normal ledger keeps every summary row and
its compact search index in the initial HTML. Native `details` opens a small
same-origin record request; no framework runtime or remote data service is used.

## Output and fallback

- `records/<project-id>.html` is a complete, accessible static record. It uses
  the shared Observatory frame and the existing specimen plate without changing
  evidence, art or identity. The loader adopts only its validated plate.
- Each ledger drawer retains a clearly labeled full-record link for no-JavaScript,
  unavailable fetch, file browsing, error recovery and printing. Search and
  filtering still use the embedded index without a request.
- `standalone.html` keeps the complete inlined ledger, artwork, fonts, charts and
  evidence downloads. It never needs record fetches. The exhibition preview also
  retains its complete static records.
- Registry IDs, hash permalinks, QR destinations, alphabetical detail folios,
  current visible row numbering and filter/sort history retain their meanings.

## Runtime ownership

Fetch only a same-origin generated record URL for the expected stable ID, reject
redirects and unexpected documents, and resolve relative artwork/evidence links
against the record's base before insertion. Active scripts and event attributes
must never be imported. Leave original native summaries and their focus alone.

Show a live loading status and retry on failure. Closing a pending drawer aborts
its request; sequence checks also ignore stale responses when abort is unavailable
or a request has already resolved. Rapid reopen must not duplicate requests,
plates or enhancement listeners. Full-record links remain available in every state.

Retain at most three mounted closed dynamic plates; open plates are never evicted.
Eviction removes the plate and enhancement callbacks, retaining only nested
native disclosure booleans. Browser HTTP/decoded-resource caches are browser-owned;
this is a bound on retained DOM, not a promise about total process memory.

## Verification and limits

Compare initial element counts, record-request counts and matched viewport
screenshots. Exercise failures, retries, interrupted opens, duplicate toggles,
eviction/reopen, hash links, filters, Back/Forward, keyboard, narrow layout,
no-JavaScript and standalone paths. Existing PR CI uploads browser screenshots.

HTML/transfer bytes, decoded image pixels, JS heap, DOM storage and GPU surfaces
are different measurements. A smaller DOM does not establish a particular RAM
saving. Keep the current responsive hero resources, lazy plate images, deferred
plate enhancement and offscreen/hidden-tab motion pauses.
