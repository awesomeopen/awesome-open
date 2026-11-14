# Preserve originals once, verify final files by batch

Proposed; use only after owner review and merge of this policy/code PR.

Save each irreplaceable original, exact prompt, source captures and generation
provenance in one durable generation archive. Keep its verified restore receipt
in the durable index. Produce final WebP files, cut-outs and metadata locally;
preserve their exact committed bytes through an independently retrieved Git
candidate. Metadata corrections repeat local validation and Git verification.

This procedure replaces the finalization/publication archive requirements and
subset-plan re-packaging in [artwork recovery](artwork-recovery.md). All other
requirements there remain: storage probe, serial generation reservations,
immediate original restore, failure evidence, skips, quarantine, durable indices
and stop-on-access-failure rules. Existing generation and failure checkpoints
retain their original plan identity. Keep historical finalization archives too.

## Select a publication batch

Keep the original generation plan unchanged. The offline `artwork_candidate.py
select` command records an ordered subset, the remaining IDs as **deferred**, a
scope-change reason and the SHA-256 of the complete preceding durable index.
Retain that index and every linked archive, receipt and reservation. Deferred is
a publication disposition: existing generated, skipped, quarantined and pending
states remain in the original history. It grants no generation or retry permission.

A one-image pilot from a 40-ID plan therefore selects one ID and defers 39. Do
not classify unprocessed projects as skipped or start a second generation batch.
Keep all reservations in the active-work handoff until explicitly reconciled.
A selected ID requires a valid generation receipt and matching restored archive;
a skip or quarantine receipt cannot qualify. Conflicting evidence requires review.

Store the selection and selected generation receipts in the private durable index
once per selected batch, before uploading candidate assets. Restore that index
and compare its bytes. Record its exact storage identity/version and hash in the
handoff. Reusing original archives avoids re-packaging after subset changes.
New generation still uses the existing serial gate under its original plan.

## Validate and retain the candidate

1. Restore selected originals by receipt identity and archive hash. Inspect every
   archive member with the legacy helper. Compare prompts and source provenance;
   inspect actual pixels and record truthful source, rights, safety and technical
   review under the [specimen contract](../site/SPECIMEN-ART.md).
2. Produce final WebP and cut-out files deterministically with recorded versions
   and options. Preserve all existing images and manifest entries. Re-run local
   finalization when output is missing; never regenerate the original. Reuse
   matching outputs. For mixed tool versions preserve existing manifest headers;
   record this batch's processing recipe in the private index.
3. Commit only the selected two assets per project, their additions in the two
   manifests and incremental asset-lock entries. Run the full offline suite,
   builds, preview/browser and brand checks. Use `candidate` below on the clean
   committed checkout. It checks exact scope, existing-record preservation,
   original receipts, prompt equality and final hashes. Existing artwork schema
   and browser checks remain responsible for formats, provenance and display.
4. Push one ordinary batch branch and open its scoped artwork draft PR. Independently
   fetch that remote branch into a fresh checkout, verify its head, and run
   `candidate` there with the same recovered inputs. Compare the two output files
   byte-for-byte. Preserve the remote repository, branch, PR, full commit and
   candidate report in the durable batch index. Restore the index after this
   batch checkpoint. A local commit or successful push response alone is insufficient.
5. After a metadata correction, repeat affected local checks, commit/push and
   remote verification. The full exact-head CI/publication gate still applies.
   The durable index's stable branch/PR locator allows recovery of later heads;
   a fresh external archive/index update is unnecessary for every correction.
   Verify the fetched head and checks anew on resume; never reuse an older report
   as evidence for a later head. Retain the branch until merge and the merged Git
   history thereafter. Do not delete the sole remote candidate before replacement
   durability is verified.
6. Follow all current main/overlap checks, exact-head CI, PR protection and Pages
   verification requirements. Only valid new-artwork-only PRs have standing
   publication authorization. Policy/code PRs remain subject to owner review.

If interrupted before step 4 completes, restore the originals and reproduce the
unretained outputs. If remote verification fails, hold publication and preserve
local output. Shared storage/access failures and uncertain previous operations
keep their existing stop/reconciliation rules; this procedure grants no route
around a denial. The offline helper records byte/identity evidence; the operator
performs real external reads and checks truthful reviews and conflicting history.

```sh
python3 scripts/artwork_candidate.py select --plan tmp/art/plan.json \
  --history tmp/art/prior-index.json --project-id FULL_PROJECT_ID \
  --reason 'Owner-requested one-image pilot; remaining IDs deferred' \
  --output tmp/art/selection.json
# receipts.json maps exactly the selected IDs to their original generation receipts.
# archives/ contains independently restored <archive-sha256>.zip files.
python3 scripts/artwork_candidate.py candidate --selection tmp/art/selection.json \
  --history tmp/art/prior-index.json --receipts tmp/art/receipts.json \
  --archives tmp/art/archives --root . --base FULL_BASE_COMMIT \
  --output tmp/art/candidate.json
```

Outputs are immutable: a retry uses a new report path or compares an existing
report. Both commands are network-free and make no generation calls. Plan,
receipts, private source captures and recovery references stay outside Git.

## Transfer cost

For N new originals, both procedures require N generation uploads and N independent
restores, plus their durable receipt/index updates and renewed storage probes.
The legacy procedure additionally needs N finalization upload/restore pairs and
one publication pair; every corrected project repeats its finalization pair.
This procedure needs two small index upload/restore pairs per publication batch
(selection and initial remote-candidate checkpoint), plus one batch Git push and
independent fetch. Each correction needs a Git push/fetch and validation. With
40-image batches, 900 images need 23 publication batches rather than 900 separate
PRs. These are operation counts, not measured throughput or service guarantees.
