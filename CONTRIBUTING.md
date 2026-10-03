# Contributing

## Scope

Awesome Open catalogs software projects whose names begin with **Open**. This naming convention is the sole defining criterion for inclusion. Capitalization, spacing, and punctuation do not alter eligibility: `OpenSomething`, `Open Something`, `openSomething`, and `Open-Something` are equivalent forms. Use the project's own spelling, and link to an official source that establishes its name and purpose.

The word must belong to the software's name. An organization named OpenSomething does not make all its products eligible, and describing software as “open source,” “open access,” or “open standards” does not qualify it. A documented expanded name qualifies when the project commonly uses an abbreviation, such as Open Broadcaster Software (OBS).

Licensing, source availability, pricing, popularity, maturity, and maintenance status are not admission criteria. Proprietary products, hosted services, libraries, command-line tools, and archived projects are welcome on the same terms. Inclusion records a name and function; it is not an endorsement or a claim that the software is open source.

## Adding or updating an entry

1. Find the appropriate functional category in [README.md](README.md), or add one and update the three-column table of contents.
2. Add the project alphabetically, using its official name and website or canonical repository. Prefer the project's own brief description; shorten marketing copy to a factual sentence describing what it does.
3. Use the existing two-column format: **Project · Description**. For GitHub repositories, append `<!-- STATS:START -->Pending refresh.<!-- STATS:END -->` to the description, on the same line. The daily workflow fills this block with plain-text metadata. For other hosts or services, leave the description alone; do not invent GitHub statistics or infer a license.
4. Repeat an entry in multiple categories when its functionality warrants it. Keep the name, link, and description consistent across occurrences.
5. Check the rendered table, links, spelling, and category anchors. Include the official source in your pull request so the name and description can be verified.

Corrections, additional categories, and newly discovered projects are welcome. There is no minimum star count, release age, or requirement to have used a project personally. Keep descriptions concise and omit promotional claims.

Contributions to this list are made under [CC0-1.0](LICENSE.md). Listed projects retain their own licenses.

## Automated metadata

[Update Dynamic Text](.github/workflows/update-stats.yml) runs daily at 00:00 UTC and can also be started from the Actions tab. It refreshes the marked blocks using GitHub's repository API and commits only when the text changes. The workflow uses the built-in `GITHUB_TOKEN`; no personal token is required.

`Created` is the GitHub repository creation date, and `Updated` is its last push date, both in UTC. These are repository dates, not original project launch dates or release dates. `License` is the SPDX identifier detected by GitHub; `Not identified` means GitHub could not identify one. Star counts use compact `k` and `m` notation. Projects hosted elsewhere have no generated metadata.

Edit descriptions outside the comment markers. To check the updater locally, run `python3 -m unittest discover -s scripts -p 'test_*.py'`. To refresh metadata, set `GH_TOKEN` and run `python3 scripts/update_stats.py`. Failed API requests leave the previous README intact and fail the workflow visibly.
