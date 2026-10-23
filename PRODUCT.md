# Product

<!-- impeccable:product-schema 1 -->

This is a short product record for design work. It summarizes and links to the
authoritative sources; when they disagree, [brand/foundation.md](brand/foundation.md),
[CONTRIBUTING.md](CONTRIBUTING.md) and the evidence contracts in `site/` win.
The visual specification is in [brand/README.md](brand/README.md).

## Platform

web

## Users

- **Comparers:** developers and self-hosters comparing Open*-named software and
  following official sources to judge fit for their own use.
- **Curious browsers:** people exploring the catalog for discovery and for the
  specimen field-guide world itself (artwork, jars, weekly draws, Observatory),
  without a specific tool in mind.

Both are a working definition confirmed by the owner on 2026-10-19
([B-PR123-01](brand/decisions/B-PR123-01.md)).

## Product Purpose

Awesome Open* catalogs software whose names begin with Open, as a generated README
and a static field-guide website built from one curated source
(`README.source.md`). Inclusion is a naming rule only
([scope](CONTRIBUTING.md#scope)).

Current success, set by the owner:

1. **Fast inspection:** a reader finds a project's function, official source and
   available evidence quickly.
2. **Memorable experience:** the specimen world is distinctive enough that people
   return and share it.

## Positioning

A single literal selection rule (the Open* name) combined with a fixed specimen
concept: each software record is inspected like a specimen, with original
function-led artwork, while every factual label keeps its literal, sourced
meaning. The strangeness lives in artwork and organization, never in the facts.

## Operating Context

- Routes: the main catalog ledger with search, category filters and detail
  drawers; `/observatory/` snapshot statistics; `/spotlight/` weekly draw archive;
  the jar hero; static record pages (`records/<id>.html`) and downloadable
  `catalog.json` and evidence files.
- A single serialized publisher workflow collects metrics and evidence, renders
  README and site, and deploys to GitHub Pages. Contributors edit only the
  curated source and reviewed evidence.
- Readers often arrive from the GitHub README, then browse or inspect on the site.

## Capabilities and Constraints

- Static output from Python standard-library generators in `scripts/`; authored
  CSS/JS in `site/`. Fix the generator or authored files, never built HTML.
- Search and filters work from an embedded index; detail records load lazily with
  a no-JavaScript full-record fallback ([detail loading](site/DETAIL-LOADING.md)).
- Evidence contracts are binding: each label keeps the meaning recorded in the
  [evidence contract](brand/foundation.md#evidence-contract), and copy states
  that meaning directly.
- Brand, artwork, icon and skill changes follow [AGENTS.md](AGENTS.md) and
  [brand/maintenance.md](brand/maintenance.md), with decision records per PR.
- Open, not started: specimen audio, ex-Open* frozen page, illustrations
  gallery, Open-prefix search exclusion ([TODO.md](TODO.md)).

## Brand Commitments

Name **Awesome Open*** (attached asterisk), field-guide framing **Genus Open***,
interface language **Retro-Scraperism**, drawing language **Speculative
FOSSoligy**. The specimen concept is fixed. Voice is neutral, terse and
matter-of-fact ([voice](brand/foundation.md#voice)). Visual rules live in
[brand/visual-system.md](brand/visual-system.md) and
[site/RETRO-SCRAPERISM.md](site/RETRO-SCRAPERISM.md).

## Evidence on Hand

Cached GitHub metrics, HN evidence, star history, reviewed alternatives,
function summaries, an eight-project deployment pilot and reviewed specimen
artwork, each under its own contract in `data/` and `site/`. Coverage of
summaries, artwork and deployment evidence is partial. There are no
testimonials, user counts, endorsements or audience research; do not invent them.

## Product Principles

1. Facts stay literal; design never erases uncertainty or provenance.
2. Inspection first: the evidence a comparer needs is never more than one
   predictable step away.
3. Wonder lives in the artwork and organization.
4. One curated source, one publisher; every view is generated from it.
5. Missing work is omitted.

## Accessibility & Inclusion

Plain labeled controls, visible keyboard focus, roughly 44px targets, native
disclosures, hover never the only route to a fact, reduced-motion fallbacks and
pause controls for decorative motion, usable narrow-screen reading
([accessibility rules](site/RETRO-SCRAPERISM.md)).
