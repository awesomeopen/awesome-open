# From a project lead to a public listing

Awesome Open* verifies a project's identity and function, adds a short catalog
entry, then publishes it. Illustrations and detailed evidence can follow later.
This document describes the current workflow and supplies labels for a flowchart.
The proposed URL form is planned separately in [Submit project](site/SUBMISSIONS.md).

## Entry points today

- **Public contributor:** the website's “Submit a project” link opens
  [CONTRIBUTING.md](CONTRIBUTING.md). The contributor prepares a catalog pull request.
- **Owner request:** the owner supplies a project URL to the assistant for research.
- **Discovery:** the separately hosted discovery task searches for missing projects.

The current website has no submission endpoint or URL-processing queue. Repository
issues can hold discussion, but no issue-triggered research consumer is implemented.
The hosted task's registration is separate from this repository; its public
operating contract is in the [automation inventory](automation/README.md).

## Main path

| Step | Actor | Action and output |
| --- | --- | --- |
| 1. Receive a lead | Contributor, owner or discovery task | Identify an official project website or repository. |
| 2. Verify the project | Contributor or assistant | Read official sources. Establish the software's name, function and canonical URL. |
| 3. Check eligibility and duplicates | Contributor or assistant | Confirm an Open-prefixed software name, including a documented expanded name. Compare canonical URLs, redirects, aliases and open proposals. |
| 4. Prepare the catalog entry | Contributor or assistant | Write a concise factual description in the appropriate alphabetical category of `README.source.md`. Cross-category entries share one canonical identity. |
| 5. Validate and accept | Contributor, assistant and repository owner | Run offline tests and inspect the README preview. Ordinary contributions use a PR and owner merge. Authorized discovery additions may commit the source-only change directly to main; branch restrictions require a draft PR instead. |
| 6. Build the publication | Repository publisher | On a relevant main change, fetch fresh main, collect available metadata, render README and cached evidence, and run validation. Commit generated output through the serialized publisher. |
| 7. Publish and verify | Publisher and operator | Successful generation updates the repository README. Build the website from the accepted published revision, then deploy it to Pages; verify the accepted entry in the published output. |

A project may be hosted, paid, proprietary, small or archived. Name and function
are the admission criteria; the detailed policy is in
[Contributing](CONTRIBUTING.md#scope). Unknown metadata stays unknown. The
publisher also runs daily and on manual dispatch; those runs refresh accepted
catalog content rather than reviewing new submissions.

## Branches and waiting states

- **Already listed:** point to the existing catalog record; preserve its identity.
- **Already proposed:** continue the existing proposal rather than create a duplicate.
- **Name or function unsupported:** leave the lead out, or retain it for further evidence.
- **Official source unavailable:** defer research; an inaccessible page alone proves no withdrawal.
- **Validation, access or quota failure:** retain useful prepared work and stop the affected operation until it can proceed safely.
- **PR awaiting review:** wait for the owner's decision. A passing check alone does not merge it.
- **Publication failure:** the accepted source remains in Git; repair or retry the normal publication path after the cause is resolved. Verify deployment before describing the website as updated.

## Enrichment after catalog acceptance

These are parallel, nonblocking branches from step 5:

- **Function and features:** read official documentation; write an original summary
  and supported capability notes; retain source links, revisions and review details.
- **Specimen artwork:** derive an original illustration from the project's function;
  inspect its pixels; prepare cut-outs, provenance and checksums.
- **Other evidence:** research aliases, alternatives and history under their separate
  evidence contracts. Normal collectors refresh available metrics and charts.

Authored enrichment passes its required validation and goes into a separate
scoped draft PR. A record's `approved` status makes it eligible for display;
owner merge approval remains separate. After merge, the normal publisher and
Pages flow deliver it. Missing enrichment leaves the basic listing available.

## Flowchart brief

**Title:** From project lead to public listing

**Main labels:** Lead → Verify sources → Eligible and new? → Prepare entry →
Validate and accept → Build → Public listing.

Use three actor lanes: **Submitter / discovery**, **Research and review**,
**Publication**. Split “Validate and accept” into **Contributor PR → Owner merge**
and **Authorized discovery commit**, then join at **Main source accepted**.
Show **README generated → Website built → Pages deployed** inside the publication lane.

Decision exits: **Already listed → Existing record**; **Already proposed → Existing
proposal**; **Needs evidence → Deferred**; **Ineligible → Declined**; **Checks fail → Fix and recheck**.
Show **Awaiting owner review** before the PR merge. Draw later **Function + features**,
**Artwork** and **Other evidence** branches through **Separate draft PR → Owner
merge → Publish update**, without putting them in front of the first public listing.

Use short labels, white ground, Prussian-blue structure and restrained hand-drawn
arrows in the existing [visual system](brand/visual-system.md). Keep labels as
editable text when composing the final graphic. Include a text equivalent and
clear arrow directions. For the proposed public-form infographic, prepend the
new intake steps only after they exist; its implementation plan is linked above.

## Implementation references

- [Contribution and publication contract](CONTRIBUTING.md#source-previews-and-publication)
- [Publisher workflow](.github/workflows/update-stats.yml) and [publisher script](scripts/publish_readme.py)
- [Website generator and current footer](scripts/build_site.py)
- [Function summaries](site/FUNCTION-SUMMARIES.md) and [specimen artwork](site/SPECIMEN-ART.md)
- [Hosted task scopes and review gates](automation/README.md)
