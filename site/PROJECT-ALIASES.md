# Reviewed project aliases

`README.source.md` owns the current display name. The canonical URL owns the
project ID, permalink and evidence keys. An official abbreviated display name
can remain eligible through a documented expanded Open name. Renaming the
label does not rename repositories, move evidence or merge projects.

## Optional curated source

`data/project_aliases.json` is optional; a project can remain without an alias
record when no alternate name has been verified.
Schema 1 has a `projects` list. Each record contains:

- `project_url`: the catalog's canonical URL.
- `aliases`: one to ten objects with `name`, an official HTTPS `source_url`, and
  optional boolean `ambiguous` (for example, OBS also names Open Build Service).
- `checked_at`: an ISO UTC review date.
- `reviewed_by`: the reviewer.

Only reviewed, evidenced names belong here. Do not infer expansions, common
misspellings or arbitrary search keywords. Names must be plain text, with no
control characters or markup. Duplicate normalized names within a project and
unknown catalog URLs fail validation. Different projects may share an alias;
they remain separate identities. An alias may repeat the display name when its
source also supports explicit reuse elsewhere.

The full catalog JSON preserves aliases and their review evidence. The compact
embedded search index keeps alias names only, and the ledger matches against
it without a live fetch.

## Search behavior

Queries still AND whitespace-separated tokens across names, descriptions,
reviewed alternative names and aliases. Existing ordinary fields keep substring
matching. Alias-only text matches at Unicode word boundaries; it does not
introduce partial-word hits. When a token exactly equals a reviewed short alias
(one to four letters/numbers/underscores), that token also uses boundaries in
ordinary fields. Thus `OBS` finds a real OBS name, not incidental `obsolete` or
`observatory` prose. Matching folds case and accents; punctuation is literal.
Other filter, URL-state and stars/name/push sorting behavior is unchanged. There
is no relevance score. Alias collisions can return more than one project.

Observatory counts and Shared names remain display-name-only. Aliases do not
create extra projects, category memberships or name groups. The separate
Open-prefix exclusion idea is not implemented here.

## Explicit HN reuse

Search aliases never become HN attribution automatically. An already reviewed
identity in `data/hn_projects.json` can opt in with `catalog_aliases`, a list of
objects naming exact aliases from the same canonical project's record. Each
reference may supply its own `context_pattern`; short aliases (up to four
word characters) and aliases marked ambiguous require nonempty reviewed
context that cannot match empty text. Context must actually disambiguate the
project. Generic software, Linux or build language is insufficient for OBS.

Resolution adds only these named aliases to discovery queries and a separate
`catalog_title_aliases` rule list. Full names and context-constrained short
names use title word boundaries. Existing domain/repository rules and existing
reviewed `title_aliases` remain separate. Resolved names, context and queries
and the source/review evidence enter the HN identity fingerprint; a substantive rule/query change requires a
complete new collection. Partial or failed collections never publish complete
counts. Budgets, schedules and publisher ownership remain unchanged.

## Display-name compatibility and provenance

The historical full-identity hash format is retained. A cached observation is
reusable across a display-only rename only after its original hash is verified
against its original stored identity and every field except `name` agrees with
the current identity. Current chart labels use the current catalog name. The
original last-good payload, hash, retrieval time and archive remain intact.
Pending pages survive a rename only when their original identity can be proved
from the stored last-good observation; otherwise they restart conservatively.
Any matching/query/provenance change still invalidates current-window reuse.

The existing offline preview contract remains: a source-only HN rule edit uses
cached evidence until the publisher refreshes. During refresh, incompatible
last-good evidence stays retained but is withheld from current charts until a
new complete result exists. No old observation is relabeled as newly collected.

## First example: OBS Studio

The [official homepage](https://obsproject.com/) uses OBS Studio and identifies
OBS and Open Broadcaster Software in its trademark notice. These are the three
reviewed names; “Open Broadcast Studio” is not seeded. The canonical GitHub URL,
registry ID, summary and assets are unchanged.

This seed changes display/search only. OBS's existing HN coverage remains
repository-URL-only, with its valid seven-story collection intact. Neither full
name nor bare OBS is opted into HN title matching in this change. Broader HN
coverage would be a separate reviewed identity change and recollection.

## Bounded enrichment job

The [alias-backfill operating contract](../automation/backfill-project-aliases.md)
defines a separate assistant-hosted queue: at most ten canonical projects per
run, three flexible runs per day, and one pending alias batch awaiting review.
Execution uses the merged contract and a separately verified hosted registration.
It adds only missing, officially evidenced records through data-only draft PRs.
Existing records and HN attribution remain unchanged. A project without an
evidenced alternate name is a valid skipped outcome, with no placeholder record.
