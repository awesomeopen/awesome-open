# Private Git archive for artwork recovery

Merged in [PR #339](https://github.com/awesomeopen/awesome-open/pull/339) on
2026-11-16 at `0e82031db665e99973c7b59c61a9c34d39dbbb7e`. This policy
prepares recovery for roughly 900 remaining illustrations and a curated catalog
of about 1,000 projects. It changes the private retention transport; the merged
[batch candidate procedure](artwork-candidates.md) and all
[recovery gates](artwork-recovery.md) remain in force.

## Prerequisites

The owner must identify a separate, dedicated **private** repository and its
retained branch. Verify its actual owner/name, repository ID, private visibility,
authorized supported write/read access, retention, capacity and recovery access
before sending any bytes. The OpenOCD pilot verified a private destination; its
identity and recovery locators remain in the private handoff. Recheck access for
each resumed run. A search finding
only the public catalog does not establish an archive. Repository creation,
connection, credentials, permissions and settings require separate authorization;
this policy neither creates nor authorizes those changes.

Preserve existing Drive archives, versions, receipts and unresolved failures.
Do not retry denied Drive operations or switch transport to evade a denial.
A policy merge alone does not reverse an access decision. Check materially new
relevant evidence before any denied action is retried; reconcile uncertain
outcomes first. A Git permission failure stops dependent transfers and generation.

Raw generation originals, complete prompts, source captures, provenance, plans,
reservations, failure evidence and recovery locators belong in the private
archive. Never upload them as public recovery files, PR attachments, logs or CI
artifacts. Public artwork PRs retain only the reviewed publication scope and
manifest required by the specimen contract. A privacy or rights conflict in a
required manifest field blocks publication pending review; do not silently omit
or alter required provenance.

## Store once and restore independently

1. Preserve the original generation ZIP byte-for-byte, with its original plan,
   full prompt, consulted source bytes and actual tool/output provenance. Use
   content-addressed paths such as `archives/<archive-sha256>.zip`. Retain skip,
   quarantine, reservation and historical index bytes unchanged. Add new index
   versions under distinct paths; keep their predecessor hashes and all referenced
   objects. Use ordinary fast-forward commits and pushes; never rewrite retained
   history, force-push or delete the only recoverable copy.
2. Record the remote repository identity, retained branch, full immutable commit,
   archive path, byte count and SHA-256 in the private handoff. The branch keeps
   the commit reachable; restore from the recorded commit, not a moving tip.
   For `artwork_checkpoint.py` storage fields use `provider: "github-git"`,
   `destination` as the verified repository identity, `object_id` as the exact
   path and `version` as the full commit. Never put credentials in these fields.
3. Fetch from that remote into a new independent repository with no local clone
   source, reference repository, alternates, shared object store or reused cache.
   Verify the fetched commit and repository identity. Materialize actual ZIP and
   evidence bytes; a push response, local copy, Git object name or LFS pointer
   is insufficient. Check the ZIP byte count and SHA-256, then run the existing
   `verify-restore` against the preserved original. It validates member hashes,
   plan, project and artifact roles. Fail closed on missing or mismatched bytes.
4. Append the resulting receipt and updated run index in the private archive,
   push and independently restore that checkpoint too. Compare exact index and
   receipt bytes/hashes; record its commit, paths and hashes outside the disposable
   computer in the private handoff. An index references the earlier immutable
   archive commit; its own commit is recorded by this later receipt/handoff to
   avoid self-reference. A fresh executor must be able to recover the plan,
   complete index chain and referenced archives from those locators alone.
5. Before new generation, round-trip the existing small probe by the same route.
   Renew it after executor restart, destination/credential change or 24 hours.
   Keep `begin`, one in-flight reservation, per-image restore and durable index
   completion before the next image. Skips and quarantine retain their exact
   evidence and retry restrictions. A publication batch may select up to 40 IDs;
   generation durability cannot be postponed until all 40 are complete.

The existing helpers remain offline byte validators; operators must establish
remote identity, privacy and genuine independent retrieval. Test fixtures using
local copies do not establish remote recovery. Where an old receipt names Drive,
keep it intact and append a Git restore receipt and migration mapping in the new
index. Check any selected receipt against its actual restored archive and original
plan. Retain the full prior index, outstanding reservations, skips and holds.

## Bounded capacity plan

Use ordinary Git for the pilot; LFS is not enabled by this policy. A supplied
metadata-only sample of 20 generation ZIPs totals 43,345,274 bytes, ranging from
1,528,362 to 2,703,970 bytes (mean 2,167,263.7). At that mean, 900 originals would
be about 1.95 GB / 1.82 GiB, 1,000 about 2.17 GB / 2.02 GiB, and 40 about 86.7 MB,
before history and overhead. This single batch is not a representative capacity
guarantee. The supplied OpenOCD checkpoint is 1,685,737 bytes, including a
1,663,879-byte original PNG; the pilot verified these bytes by independent restore.

GitHub's [large-file guidance](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)
blocks files over 100 MiB, recommends repositories ideally below 1 GB and strongly
below 5 GB, and cautions that Git is not a backup service. Its
[repository limits](https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits)
also list a 10 GB on-disk recommendation; use the more conservative guidance here.
The [single-push limit](https://docs.github.com/en/get-started/using-git/troubleshooting-the-2-gb-push-limit)
is 2 GiB. Sources checked 2026-11-16. These limits do not promise account capacity
or transfer performance.

Keep the helper's 32 MiB per-archive limit. Before each transfer, measure actual
new bytes and projected repository growth; cap each push at 128 MiB of new
uncompressed Git object content, including index updates. Split transfers into
ordinary incremental commits below that cap when necessary. Measure retained
history and fresh clone size/time after the pilot and every publication batch;
avoid repeated binary copies or ZIP rewrites. Full independent restores consume
bandwidth and disk even when generation archives are stored once.

Before cumulative archived payload or measured Git storage reaches 750 MB,
pause expansion for an owner-reviewed capacity decision with actual sizes,
projection through the remaining catalog, history overhead, clone duration and
available storage/bandwidth. The sample already projects beyond the ideal 1 GB:
this policy permits a measured pilot, not an unreviewed 900-image rollout.
Resume only with a documented retention/capacity plan. Do not split repositories,
prune history or buy storage automatically. LFS requires demonstrated need,
verified account plan, storage and bandwidth quota, approved budget and retention,
and a clean restore that materializes and hashes every actual LFS object. No LFS
quota is currently known. Missing objects or exhausted quota block recovery.

## Verified OpenOCD pilot

The owner opened [PR #373](https://github.com/awesomeopen/awesome-open/pull/373),
which merged on 2026-11-21 at `ef935161b1c2239f5221c9f031d3fe27f96560d6`.
The pilot reused the preserved original, verified independent archive and
PR-linked index restores, and compared independently fetched candidate bytes.
Exact-head CI passed. The normal [publisher and Pages run](https://github.com/awesomeopen/awesome-open/actions/runs/44870888317)
deployed `443cdae3f14581b05cdb573e5e70d3feb882c362`; the live record references
the cutout, and both served artwork files matched the candidate hashes.

For scheduled reuse, [OpenUtau PR #379](https://github.com/awesomeopen/awesome-open/pull/379)
opened on 2026-11-21 with the preserved 2026-11-12 original. Independent candidate
and PR-linked index restores were verified before the owner merged it on
2026-11-23. The normal [publisher and Pages run](https://github.com/awesomeopen/awesome-open/actions/runs/45171230504)
succeeded, and served original/cutout bytes matched the verified candidate.
This provides a reuse example alongside the owner-opened OpenOCD pilot; each
resumed batch still requires fresh access, capacity, recovery and exact-head checks.

Keep the original plan, deferred IDs, unresolved holds and recovery locators in
the private handoff. Resume through the existing prerequisites and candidate
procedure. This owner-opened pilot does not establish that the earlier assistant
PR-creation denial has been resolved; any future denial stops the affected action.

Contribution by Junge (AI)
