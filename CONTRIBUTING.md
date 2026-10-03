# Contributing

## Scope

Awesome Open catalogs software projects whose names begin with **Open**. This naming convention is the sole defining criterion for inclusion. Capitalization, spacing, and punctuation do not alter eligibility: `OpenSomething`, `Open Something`, `openSomething`, and `Open-Something` are equivalent forms. Use the project's own spelling, and link to an official source that establishes its name and purpose.

The word must belong to the software's name. An organization named OpenSomething does not make all its products eligible, and describing software as “open source,” “open access,” or “open standards” does not qualify it. A documented expanded name qualifies when the project commonly uses an abbreviation, such as Open Broadcaster Software (OBS).

Licensing, source availability, pricing, popularity, maturity, and maintenance status are not admission criteria. Proprietary products, hosted services, libraries, command-line tools, and archived projects are welcome on the same terms. Inclusion records a name and function; it is not an endorsement or a claim that the software is open source.

## Evaluating projects for your needs

If you are looking for vetted open source software or production-ready open source tools, check each project's official sources for an OSI-approved license, recent commits or releases, clear documentation, and a setup path that fits your environment. Contributions verify the project's identity and basic description; production readiness and security require a separate assessment for your use case.

## Adding or updating an entry

1. Find the appropriate functional category in [README.md](README.md), or add one and update the three-column table of contents.
2. Add the project alphabetically, using its official name and website or canonical repository. Prefer the project's own brief description; shorten marketing copy to a factual sentence describing what it does.
3. Use the existing two-column format: **Project · Description**. For GitHub repositories, append `<!-- STATS:START --><!-- STATS:END -->` to the description, on the same line. Leave this block empty until the daily workflow fills it with compact metadata on a separate line; do not add visible “Pending refresh” text. For other hosts or services, leave the description alone; do not invent GitHub statistics or infer a license.
4. Repeat an entry in multiple categories when its functionality warrants it. Keep the name, link, description, and alternatives consistent across occurrences.
5. Check the rendered table, links, spelling, and category anchors. Include the official source in your pull request so the name and description can be verified.

Corrections, additional categories, and newly discovered projects are welcome. There is no minimum star count, release age, or requirement to have used a project personally. Keep descriptions concise and omit promotional claims.

Contributions to this list are made under [CC0-1.0](LICENSE.md). Listed projects retain their own licenses.

## Alternatives

Keep the two-column table. When official evidence explicitly supports a relevant alternative, add `<br>Alternative to: [Name](official-evidence-URL), [Name](official-evidence-URL)` immediately after the existing description and **before** `<!-- STATS:START -->`. Use one to three targets; omit the entire line when none is verified. Do not place this manually maintained line inside generated STATS or HN markers, and do not rewrite the description to accommodate it. Entries without GitHub metadata may also use this format.

Link each target name to the project's official comparison, alternative statement, or migration guide, rather than a generic product homepage or third-party list. Record the canonical entry URL, target name, evidence URL, checked UTC date, and brief use-case scope in [`data/alternatives.json`](data/alternatives.json). Apply the same links to every category occurrence. Evidence establishes a relevant alternative, not feature parity, production suitability, or universal drop-in compatibility; migration caveats still apply.

Alternatives are curated manually. Discovery and accuracy checks remain review-only: proposed additions or corrections need review before changing the README or evidence. Neither daily updater populates alternatives. Tests validate link placement, evidence agreement, cross-category consistency, and preservation during metadata/chart regeneration.

## Automated metadata

[Update Dynamic Text](.github/workflows/update-stats.yml) runs daily at 00:00 UTC and can also be started from the Actions tab. It refreshes the marked blocks using GitHub's repository API, highlights category leaders, and commits only when generated content changes. The workflow uses the built-in `GITHUB_TOKEN`; no personal token is required.

Metadata is rendered as `<br><sub>creation-date -- last-push-date / SPDX-license / stars</sub>`. The first date is the GitHub repository creation date, and the second is its last push date, both in UTC. The last push date is wrapped in `<b>` once its 12-calendar-month anniversary is reached (inclusive, based on today in UTC; February 29 anniversaries use February 28 in non-leap years). Missing or unknown dates are not emphasized. The daily refresh reevaluates this threshold. These are repository dates, not original project launch dates or release dates. The license is the SPDX identifier detected by GitHub; unknown licenses (including `NOASSERTION` and `OTHER`) are omitted. Star counts use compact `k` and `m` notation. Projects hosted elsewhere have no generated metadata.

Only the three highest-starred GitHub repository name links within each category are bold. Categories with fewer than three eligible repositories highlight all of them; exact star-count ties use the lowercase canonical repository path alphabetically. Cross-listed projects are ranked separately in each category. Ranking uses the unrounded API count and never reorders entries. This highlighting is independent of HN chart coverage.

Edit descriptions outside the comment markers. To check the updater locally, run `python3 -m unittest discover -s scripts -p 'test_*.py'`. To refresh metadata, set `GH_TOKEN` and run `python3 scripts/update_stats.py`. Failed API requests leave the previous README intact and fail the workflow visibly.


## Hacker News attention sparklines

Selected names have a clickable 120 × 24 static SVG below them, with matching alt and title text `HN discussions / 2y`. The image itself links to HN search; there is no extra discussion text link. Bars show deduplicated story submissions matching a verified project identity per UTC month over the last 24 **completed** months, oldest at left. All eligible charts use the same zero-based square-root vertical scale: bar height is `20 × sqrt(monthly count / shared monthly maximum)` pixels. The maximum is shared across all eligible projects and months, so equal counts have equal heights; the square-root transform makes low counts easier to see while preserving their ordering. This measures attention, including critical or controversial coverage, not endorsement, quality, votes, historical popularity, or sentiment.

The initial research shortlist and identity rules are in [`data/hn_projects.json`](data/hn_projects.json). The generated [`data/hn_evidence.json`](data/hn_evidence.json) records the exact window, monthly counts, accepted and excluded story IDs, titles, URLs, identity reasons, API query sources, and eligibility. A chart requires at least six matching stories across at least three months. Projects without a chart may have sparse history, ambiguous identity, or be outside the researched shortlist; absence is not evidence of no HN discussion. Matching uses verified official URL hosts/repository paths or explicit project names in story titles, with extra checks for ambiguous names. Comparisons, integrations, and third-party articles that mention a project can count; the chart is not restricted to first-party announcements. Search coverage is best-effort, based on HN's Algolia index. The linked search is for browsing and may include different matches than the audited chart.

The existing daily workflow checks whether the completed-month window has changed and only then downloads new HN evidence, without credentials or an external chart service. Run `python3 scripts/update_hn.py --refresh` to force collection, or `python3 scripts/update_hn.py --render-only` to reproduce checked-in SVGs and README links offline. Network failures stop before publishing partial evidence. SVG titles/descriptions include the time window, monthly counts, and shared square-root scale. Do not edit generated `<!-- HN:START -->` blocks or SVGs manually; update the identity mapping and refresh instead. Review identity aliases especially carefully for common project names.

The updater never force-pushes. If another contributor or automation updates the branch during a refresh, the push fails safely; rerun against the new branch tip rather than overwriting concurrent edits.
