# Reviewed deployment and installation evidence

The optional `data/deployment_evidence.json` input supplements expanded project records and two website filters. It does not change README descriptions, Function prose, ranking, release/Scorecard providers, or the publisher's collection schedule. All builds remain offline. No candidate software is installed or probed.

## Identity and review

Use `schema_version: 1` and a `projects` object keyed by the catalog's full SHA-256 canonical-URL ID. Copy both the ID and `project_url` from the freshly built catalog; website and non-GitHub identities work identically. Cross-listed projects get one record. Unknown IDs and URL mismatches fail validation.

Every record needs `project_url`, `review_status` (`pending`, `approved`, `rejected`), `checked_at` (actual ISO UTC review date), `reviewed_by`, `review_note`, and named `sources`. Approved means source-reviewed and eligible for the proposed build, **not** owner approval or permission to merge. Pending/rejected records are validated but not rendered. Keep review identity explicit, including AI review. Do not advance dates without reviewing claims again.

Each source has an HTTPS `url`, a `title`, and `kind`: `upstream_docs`, `upstream_repository`, `registry`, or `distribution`. An optional `revision` must be a verified full Git commit SHA. A live documentation URL without revision is a dated observation, not immutable evidence. Fact `source_ids` reference these source keys.

## Sparse, multi-valued facts

All six fact lists are optional. Omit an unknown field rather than use an empty list, null, false, zero, or an unsupported claim. Every listed fact has a nonempty `scope` and `source_ids`. At least one sourced fact is required per record.

- `run_modes`: `value` is `cli`, `desktop`, `local_web`, `server`, `library`, or `firmware`.
- `install_methods`: `value` is `binary`, `installer`, `container`, `package_manager`, `source`, or `firmware_image`. A binary can be a downloadable archive. Describe concrete tools, language-package installs, Compose/Helm, and exceptions in scope. More than one mode and method may apply.
- `platforms`: `value` is the explicitly documented OS/architecture description. Scope it to the release, package, runtime, or deployment path. A Dockerfile does not establish host/architecture support.
- `external_services`: `name` plus `requirement`: `required`, `optional`, or `configuration-dependent`. Distinguish an application from a separate model backend or resource provider. No entry does not mean no external service is needed.
- `packages`: exact `ecosystem`, `coordinate`, `channel`, `status`, and `upstream_relationship`. Status is a source observation: `documented`, `disabled`, `deprecated`, or `discontinued`. It is not a current installability guarantee. Relationship is `upstream`, `community`, `distribution`, `third-party`, or `unknown`. Upstream documentation of a community package does not prove upstream maintenance. Explain that distinction in scope. Never substitute universal availability booleans or infer package identity from a similar name.
- `requirements`: `kind` (`minimum`, `recommended`, `default`, `constraint`) and a sourced `note`. Include units and workload/version/deployment qualification in the note/scope. Keep application and model/cluster requirements separate. Do not turn defaults into minima or publish a benchmark, universal footprint, security, health, or deployment-ease score.

The initial eight records are a coverage pilot, not exhaustive package or platform inventories. The OpenSCAD stable Homebrew disabled state is intentionally represented separately from the snapshot cask. OpenWrt requires device-specific compatibility review, not one universal RAM threshold.

## Filters and missing data

“Reviewed run mode” and “Reviewed install method” each select one documented value; the record itself can contain several. Combining the two filters intersects matches. “Any / not reviewed” keeps all records. “Not recorded” selects absence of that fact in approved evidence; it does not mean unsupported. Search and ranking retain their existing meanings. URL parameters `run_mode` and `install_method` restore with reload/Back/Forward and reset with other filters. Without JavaScript, all records and source links remain in native disclosures.

## Review workflow

1. Inspect fresh main and pending evidence/Function/design PRs before editing. Preserve existing records and every unrelated field.
2. Read primary sources and verify each exact project/package identity. Registry and distribution sources can establish their own packaging state; upstream relationship needs separate evidence. Never run candidate installers or commands from sources.
3. Add only verified, useful scoped facts. Explain incomplete coverage and review limitations. Separate this structured data from Function summaries; do not rewrite either short descriptions or Function prose to fit a filter.
4. Run the full Python suite, Node tests, offline README/catalog/site/preview builds and existing browser check. The browser check includes setup filters, URL/history/reset, keyboard disclosures, narrow screens, no-JavaScript and standalone coverage. Inspect generated screenshots.
5. Commit only curated evidence, implementation, tests and documentation. Never commit generated README, metrics snapshots, preview output or screenshots. Open a review-only draft PR and report its exact head/checks; do not merge, force-push or publish.

No new collectors, services, credentials, external cron, workflow permissions or security settings are introduced. Updating stale evidence is a separate reviewed change. Missing input files continue to build successfully and add no deployment facts.

## Function summary integration

The catalog accepts Function summaries and keyword-only `deployment_evidence` as separate optional inputs. Both loaders run in CLI/site builds. Source-reviewed prose remains in the Function section; structured setup facts render after the existing evidence cards within the same expanded record. The jar hero, folded row, short description, Function content and existing evidence-card layout remain unchanged. Regression coverage checks the three overlapping Function/setup pilot records, along with the five setup-only records. No Function source text or review dates are rewritten by this feature.
