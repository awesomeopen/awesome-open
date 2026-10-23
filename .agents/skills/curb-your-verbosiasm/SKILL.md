---
name: curb-your-verbosiasm
description: Write and edit Awesome Open* documentation, knowledgebase articles, help text, and explanatory interface copy around the reader's main question. Use when content buries its point, exposes unnecessary implementation complexity, repeats caveats, or needs a clearer explanation with fewer words. Apply structural editing, positive statements, and selective examples while preserving evidence and useful detail. Also use when the user names Curb your verbosiasm or requests an Awesome Open anti-slop review.
---

# Curb your verbosiasm

Make the main point easy to find, understand, and use. Treat Awesome Open* as a
list of software named Open. Let readers browse the list, understand a record,
and follow its sources. Explain the machinery at the depth their task requires.

## Establish the reader's question

Read the whole passage and its immediate surroundings before editing. Identify
the reader, the question they came to answer, and what they should be able to do
after reading. Use the supplied context; ask only when a missing fact changes
the answer.

State the answer in one working sentence. Use it to decide what belongs. Keep
this planning sentence internal unless it also makes the best opening. For a
long page, identify one purpose for each section and remove overlapping sections.

In a repository task, read `AGENTS.md`, `brand/foundation.md`, and the writing
section of `site/RETRO-SCRAPERISM.md`; consult `CONTRIBUTING.md` for inclusion
claims. Follow the current project contract. When working from a pasted passage,
use its established facts and flag consequential gaps rather than inventing
repository behavior. Consult [repository integration](references/repository.md)
for source locations, checks, and the earlier positive-statement cleanup.

## Rebuild the explanation around the answer

1. **Lead with useful information.** Put the answer, action, or definition first.
   Give prerequisites first when the reader needs them to act safely or correctly.
2. **Choose what earns space.** Keep a sentence when it answers the question,
   supplies necessary evidence, enables an action, or prevents a likely material
   mistake. Remove process narration, self-description, praise, speculative
   objections, and repeated conclusions. Fix a weak underlying claim before
   polishing its wording.
3. **Put detail at the right depth.** Keep the result and essential qualification
   together. Put supporting mechanics in the relevant method, contributor guide,
   or existing disclosure, and link to them. Prefer deleting redundant detail to
   moving it into another box. Preserve the information needed for the current
   task where the reader can find it.
4. **Prefer concrete explanation.** Name the thing, say what happens, and give the
   consequence when it helps. Use stable terms for the same object. Keep technical
   vocabulary that the intended reader needs; explain an unfamiliar term once.
5. **Try one example.** If an abstract rule still takes effort, test whether a
   short `Example: ...` can replace part of the explanation. Use a sourced case
   or clearly labeled hypothetical. Keep the example only if it resolves a real
   ambiguity or shows the reader how to apply the rule. Omit it when the answer
   already stands on its own.
6. **Read the result as a whole.** Check the opening, sequence, links, and ending.
   Remove a recap when the last concrete point already completes the answer.

Spend words where they save reader effort. Prefer equal or shorter total copy,
including headings, examples, tooltips, and disclosures added by the edit. Add
length only to restore a missing fact, prerequisite, or necessary explanation.
Keep a clear passage intact. Avoid compressing it into cryptic labels or dense
sentences merely to lower the word count.

## State what the thing is

Define values, rules, and states positively. Replace a defensive contrast with
the useful fact. For example, write “The inventory records the scheduled tasks
as of 23 October 2026.” Keep the date; remove the imagined alternative.

For every caveat, identify the mistake it prevents. If it merely rebuts a claim
the text never made, delete it. If it changes how to use the information, retain
its substance in a direct statement at the point of use or once in the method.
Keep specific prerequisites, rights restrictions, warnings, unavailable states,
and genuine uncertainty. Preserve literal instructions such as “Do not commit
credentials.” Never turn an unknown value into zero, an observation into a
recommendation, or a documented setup into a tested installation.

Preserve verification status explicitly when the source supplies it. A reference
to documentation alone leaves installation testing ambiguous; retain “Installation
status: untested” or equally clear wording. Use “pending” only when testing is
actually planned. Apply the same care to unknown compatibility and failed checks.

Preserve each metric's subject, units, time window, date, and relevant scope.
For retained monthly stars, keep the retention/fetch qualification. For a failed
refresh, keep the observation date and stale status. Use the repository's
evidence contract to check meaning; keep its review-only excluded readings out
of reader-facing copy.

## Remove slop after the structural edit

Review each remaining sentence for an actual contribution. Cut generic openings,
unsupported importance, vague attribution, decorative abstractions, rhetorical
reveals, and commentary telling the reader how to feel about a fact. Replace
them with available specifics only when those specifics serve the question.

Use ordinary nouns and verbs. Preserve accurate terminology and the project's
neutral voice. Give lists, tables, headings, and emphasis a reading task. Keep
the specimen imagery in the artwork and established interface vocabulary;
describe software functions literally.

Treat suspicious words and sentence patterns as prompts for judgment. Do not
assign an AI-likeness score, infer authorship, impose a punctuation quota, or
run a blind replacement pass. Judge whether the reader can understand and use
the result. Consult [examples](references/examples.md) when choosing between
deletion, restructuring, and adding an example.

## Verify and deliver

Read once for comprehension and once against the source:

- Can the intended reader answer their question from the opening and follow the
  rest without reconstructing implementation history?
- Does every remaining detail have a job, with each fact explained once at the
  appropriate depth?
- Are claims, identifiers, links, numbers, dates, prerequisites, and uncertainty
  preserved? Does an example stay within the verified facts or identify itself
  as hypothetical?
- Does any added text reduce effort enough to justify its length? Is unchanged
  clear prose still intact?

For an edit, deliver the revised content. Add a brief explanation only for a
material restructuring, unresolved fact, or requested rationale. For a review,
name the main comprehension problem and show the smallest useful revision.
For repository changes, edit authored sources, use the project checks and
draft-PR workflow, and report the result concisely. Keep the editing analysis
out of the published content.
