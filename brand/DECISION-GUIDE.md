# Adding a brand decision

New decisions use `B-PR<number>-<ordinal>`: the pull request number plus a
zero-padded ordinal starting at `01`. The PR supplies a repository-unique
namespace; contributors do not reserve the next global number. Open a draft PR
with a useful, nonempty documentation or implementation commit first, then use
its assigned number for the decision records before requesting review.

Keep each new decision in `brand/decisions/<ID>.md`. Add another ordinal when
one PR contains multiple decisions. A PR number identifies where the record
originated, not whether it was approved or merged. Keep the ID and filename
stable after merge. Later changes cite the existing decision; replacements use
a new record with an explicit supersession link. Closed, unmerged PR numbers
are never reused for a different proposal.

`brand/decisions.md` retains the legacy decision register. Do not renumber its
records, rewrite its historical statuses, or change existing heading anchors.
Read the current main branch before editing; concurrent PRs may have added
legacy records before this workflow is adopted.

The complete overview will be generated from the legacy register and individual
records. Contributors edit source records, never a shared generated table.
Validation and the generator are being added in this draft PR. The completed
change will document record metadata, local commands, and CI review output here.

Contribution by Junge (AI)
