# Specimen voices: proposed feature and audition plan

Status: **experiments failed; direction replaced**. On 2026-10-18 the owner
listened to the test batches below and ended the attempt to steer TTS models
toward interpretative, function-derived character voices. The work continues on
a different path: a consented cloned voice reading the plain name, plus a quiet
ambient "scene" beneath it (proposed in
[B-PR121-01](../brand/decisions/B-PR121-01.md)). See
[Outcome](#outcome-experiments-failed) and
[Next path](#next-path-cloned-name-voice-and-ambient-scene). The sections below
are kept as the record of what was tried. This document does not install a
model, enable a service, authorize spending, change the site, or extend existing
artwork approval to audio.

## Direction

For each project, ask: **How would this tool sound if it spoke?** Read its official
repository and documentation, then derive a fictional voice description from its
actual function, operating model and interaction patterns. The analogy can be
strange; the spoken facts remain literal. Use the same independently conceived,
function-led approach as [specimen illustration](SPECIMEN-ART.md), rather than
assigning every project one of a few stock fictional narrators.

Seek variation in resonance, texture, register, rhythm, articulation and spatial
character. Do not make every voice low, robotic, breathy or metallic. Maintain
intelligibility at ordinary listening volume. Do not imitate identifiable people
or imply a project's endorsement, security, license or governance through its
voice. These are Awesome Open interpretations, not official project voices.

- Offer a **neutral voice** alongside every character voice, particularly for
  comparing pronunciation in the Observatory's proposed rhyme feature.
- Use pre-generated, reviewed audio on specimen plates and for project names.
  Keep the original text visible and accessible; audio is optional.
- Generic fictional narrators are a fallback if per-project voice design proves
  impractical. A neutral-only result is preferable to unintelligible novelty.
- Keep names and factual Function summaries in the existing editorial register;
  the character comes from sound, not invented first-person claims or dialogue.

## Proposed delivery

Generate offline in a controlled pipeline, potentially on the owner's local TTS
setup, then serve static audio assets. Visitors should not require a live home
computer, credentials, microphone access or a paid inference request. STT is not
required for playback; transcription may assist internal quality checks only.

A future implementation should provide play/stop, explicit neutral/character
selection, keyboard-operable labeled controls, no autoplay and one active clip at
a time. Fetch audio only after interaction; do not preload hundreds of recordings
or add audio processing to catalog startup. Define behavior for closing a drawer,
changing voice, navigating away and missing/failed files. Keep the full record and
standalone output useful without JavaScript or audio. Use the existing specimen
plate and route conventions; this proposal does not introduce a new page shell.

For the first audition, exchange a versioned batch of prompts/settings and return
an audio archive plus the run manifest. This supports local generation without a
public backend or Tailscale Funnel. Keep failed experiments and large raw audio
out of the catalog repository; submit only deliberately selected assets later.
A live connection is a separate option to evaluate if file exchange becomes a
measured bottleneck, not a prerequisite for a pilot.

Determine audio formats, file-size budgets, hosting limits, cache invalidation and
storage outside Git if needed during the pilot. Do not publish a public endpoint
on the owner's computer merely to enable playback. Backend, account, network,
billing and access changes require their own implementation and authorization.

## Short-name generation experiment (run 2026-10-18; failed – see outcome)

One- or two-word project names deserve their own test set, separate from ordinary
Function-summary narration. The submitted model pondering raises useful failure
hypotheses: clipped beginnings/endings, repeated syllables, unstable pitch,
trailing sounds, extra speech and insufficient voice character on short input.

The suggested ranking (Maya1 best, Breeze TTS 2 good with padding, VoxCPM2 and
Qwen3-TTS poor) and a mandatory 4–10-word warm-up are **unverified hypotheses**.
The primary sources reviewed below do not establish that comparison. Architecture
alone does not predict these results; do not accept or reject a model on this
ranking. “Zero-shot” voice conditioning is not a guarantee of reliable isolated
word generation, and “warm-up” must not be confused with inference startup time.

### Candidate evidence

| Candidate | What official documentation supports | What remains untested here |
| --- | --- | --- |
| [Maya1](https://huggingface.co/maya-research/maya1) | Llama-style autoregressive model with SNAC discrete audio codes, text-described voices and an Apache-2.0 model declaration | Superiority for isolated names, artifact rate and reproducible character. Local hardware performance and same-seed reproducibility were measured 2026-10-18 – see [Pilot runtime](#pilot-runtime-as-run) |
| [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) | Discrete multi-codebook language-model approach, voice design and reuse of a generated voice reference | Claimed short-input instability or a required carrier phrase |
| [VoxCPM2](https://github.com/OpenBMB/VoxCPM) | Continuous-latent diffusion-autoregressive voice design; Apache-2.0 code/weights. Its [paper](https://arxiv.org/html/2606.06928v1) reports general TTS/control evaluations | Claimed poor one/two-word stability, mandatory warm-up and performance on the owner's machine |
| [Breeze TTS 2](https://github.com/breezeblue-ai/breeze-tts#license-and-responsible-use) | Voice design and Qwen3-TTS-derived audio tokenizer; code Apache-2.0, but weights, derivatives and self-hosted outputs restricted to research/non-commercial use | Short-name padding benefit and suitability for public catalog audio; documented Linux/CUDA runtime is not evidence of working Apple Silicon support |

Breeze is a **licensing-gated research candidate**, not an approved production
choice. The owner excluded it from the pilot on 2026-10-18: its self-hosted
outputs are non-commercial ([LICENSE](https://huggingface.co/BreezeBlue/Breeze-TTS-2/blob/main/LICENSE)
§3, and §7.3: output ownership "does not remove or limit the non-commercial
restrictions"), which this repository's CC0 dedication cannot carry.
A hosted-service license does not automatically license self-hosted output.
Check the exact release's weights, dependencies and output terms before selecting
any backend. These observations are not a substitute for release-specific review.
No paid service, free allowance, continuing free API or local throughput is
assumed by this plan.

### Reproducible audition

Start with a small pilot of 6–10 actual canonical catalog projects, including
single and two-word names, acronyms, invented spellings, punctuation, numerals and
mixed case. Record intended pronunciation and uncertainty rather than guessing
that spelling or a stylized voice establishes an official pronunciation. Include
several ordinary Function summaries as longer controls.

For each eligible model and voice, compare:

1. Direct name-only generation.
2. A carrier phrase: “The product is called {name}.”
3. A two-sentence carrier with the name isolated as its own sentence.

Repeat across multiple seeds where supported. Pin checkpoint revision, runtime,
quantization, conditioning and settings. Record prompt, spoken text, generated
duration, generation time (cold startup and warmed inference separately) and all failures,
not just the selected best output.
Listening must be performed by a person or an actually available audio-capable
reviewer; text inspection alone cannot approve sound. Ask the owner to audition
the pilot when no verified listening capability is available.
Compare neutral and unusual descriptions under the same conditions. Audition
blind when practical, scoring complete name accuracy, extra/omitted speech,
onset/ending artifacts, intelligibility and repeatable character. Transcription
is auxiliary: an ASR model can misrecognize a correctly spoken invented name.

Carrier-phrase generation is an experiment, not a promise to “trick” an encoder
into stable speech. It can affect rhythm and coarticulation as well as voice.
For each carrier output, align the **full known spoken text** to propose word
boundaries, then listen and adjust both crop boundaries. Never remove a fixed
1.2 seconds. There may be no silence before the name; speech rate, pauses and
leading silence vary, and alignment itself can fail. Preserve a clean onset and
final consonant. Reject or regenerate when the name cannot be isolated without
carrier leakage or audible damage. Retain the original recording, crop sample
positions, sample rate, alignment method and reviewer findings.

No winner or reliability claim is recorded until audition results exist. Choose
short-name and full-summary backends independently if the evidence warrants it.
License eligibility remains a separate gate from perceived audio quality.

## Pilot runtime (as run)

Recorded 2026-10-18. Measurements, not scores: nothing below says how a clip
sounds. Runner and environment live outside this repository
(`local-ai/tts/maya1_batch.py`, `dotfiles/scripts/m5-install-maya1.sh`).

**Route.** Maya1 through Hugging Face Transformers on the owner's Apple M5 Max
(macOS 27.0.1), torch 2.14.1 MPS, bf16, unquantized. Offline batch: a batch file
goes in, raw WAVs plus a run manifest come out. No endpoint, account or network
exposure is involved.

| Pinned item | Value |
| --- | --- |
| Model | `maya-research/maya1` at `b1b9b38ca9decbfcfd6c98ea93dd502bfd0f9572` |
| Decoder | `hubertsiuzdak/snac_24khz` at `d73ad176a12188fcf4f360ba3bf2c2fbbe8f58ec` (MIT) |
| Runtime | Python 3.12.14, transformers 5.20.1, snac 1.2.1 |
| Settings | temperature 0.4, top_p 0.9, repetition_penalty 1.1, max_new_tokens 2048, min_new_tokens 28 |

All weight files matched the sha256 that Hugging Face records. The official
source is `huggingface.co/maya-research/maya1`, as linked from mayaresearch.ai.
`maya1.org` states it is "not affiliated with or endorsed by Maya Research".

**Settings are a choice.** The model card's example uses temperature 0.4, while
its `generation_config.json` specifies 0.6. The card calls neither canonical.
The pilot fixes 0.4; a temperature comparison would be a separate experiment.

**Measured (40-take test batch).** Model load 1.2 s, decoder load 0.1 s. All takes
ended on the end-of-speech token.

| Condition | Takes | Audio | Mean generation time | Realtime factor |
| --- | --- | --- | --- | --- |
| Name only | 16 | 0.94–2.13 s | 1.92 s | 0.69–0.81 |
| Carrier phrase | 16 | 2.05–4.95 s | 3.61 s | 0.79–0.81 |
| Function summary | 8 | 4.61–6.06 s | 6.28 s | 0.80–0.81 |

Total: 110.8 s of audio in 138.7 s, 10.64 MB of raw 32-bit float WAV. The
first take in a run is the slowest (0.69 realtime): that is warm-up after
startup, recorded per take by order.

**Reproducibility.** The same seed and settings reproduce bit-identical samples
on MPS: three runs of six takes matched. File hashes still differ between
identical runs because libsndfile writes a timestamp into the WAV `PEAK` chunk.
Identity therefore needs a hash of the decoded samples, not of the file.

**Raw audio.** The model card's example drops the first 2048 samples (85 ms) of
decoder output as warm-up. The runner keeps them and records the offset, so that
trim follows the same crop rules as any other.

**Not used: the ComfyUI node.** `Saganaki22/ComfyUI-Maya1_TTS` repackages the
same transformers example but offers `cuda` and `cpu` only, targets transformers
4.x and was last changed 2025-11-11. ComfyUI's output cache also returns cached
results for repeated identical inputs, which defeats repeat-run measurement.

### Test batch 01

Source: `site/SPECIMEN-VOICE-PLAN_test01-prompt-plan.md`. It covers OpenSCAD,
OpenVPN, OpenRA and OpenCat, each with a function-derived character voice for
A (name), B (carrier) and C (summary), plus a neutral voice for A and B. Two takes
each, with seeds 1 and 2, give **40 clips**. The recipe states 30, which matches
no reading of its own sections. The batch has four projects, fewer than the 6–10
asked for above, and contains no numerals or internal punctuation.

Owner listening has not been scored yet. Auxiliary whisper (large-v3-turbo)
transcripts point to where to listen first, not to verdicts:

- **OpenRA** came back as "OpenRay", "Open Ray" or "OpenRAW" in 7 of 10 takes,
  across both voices and all conditions. Intended reading, letters (R-A) or a
  word: **undecided**, and needed before scoring.
- **Name-only onsets:** "Okunscad" (OpenSCAD neutral, take 02) and "Okoncat"
  (OpenCat character, take 01). Both are name-only takes.
- Every carrier and summary take for OpenSCAD, OpenVPN and OpenCat transcribed as
  written. ASR can mishear a correctly spoken invented name, so this proves nothing
  about the audio.

### Open questions this answers

- **Actual local runtime:** the route above. Measured and reproducible, but not yet
  approved.
- **Rights eligibility:** Maya1 is Apache-2.0 and the SNAC decoder MIT. Breeze is
  excluded for output licensing. A release-specific review of the dependency
  licences is still due before publication.
- **Seeds:** supported and deterministic, so takes are identified by seed rather
  than by label.
- **Projected cost of the test01 recipe across the catalog** (545 entries in
  `README.source.md`): about 5.3 h of generation and 1.45 GB of raw WAV. Raw audio
  stays outside the repository. The served format and its size budget remain open.

Still open at the time: intended pronunciations, owner listening scores, the
alignment tool for carrier crops, the served format and the neutral fallback.
Superseded by the outcome below.

### Test batch 02: other models and an accent probe

Maya1 acts only on the closed attribute vocabulary in the `prompt.txt` shipped
with its weights: age, gender, five accents, pitch, about ten timbres, pacing,
six emotions and 17 character types. Its model card notes that "unusually
detailed descriptions may not be followed consistently". Test01's free-form
creature descriptions left character and neutral voices close together (median
F0 within roughly 10–40 Hz). Rewritten in Maya1's vocabulary, the same seeds
moved clearly: OpenVPN from 155–168 to 90–92 Hz, OpenCat from 183–188 to
296–353 Hz.

Test01 was then run verbatim through two free-form voice-design models, both
Apache-2.0 [mlx-audio](https://github.com/Blaizzy/mlx-audio) 0.5.9 conversions
on the same machine: [Qwen3-TTS 1.7B VoiceDesign](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign)
and [VoxCPM2](https://huggingface.co/openbmb/VoxCPM2). Both followed the
descriptions in pitch: character voices spread over 102–334 Hz (Qwen3) and
112–314 Hz (VoxCPM2), against 140–212 Hz for Maya1. VoxCPM2 garbled most
name-only takes. All three models reproduce bit-identical samples per seed.
Maya1 was also probed across all five of its accents.

## Outcome: experiments failed

The owner auditioned test batches 01 and 02 on 2026-10-18 and judged the attempt
failed. The models can be steered in pitch, pace, a closed set of timbres and
accents, but not toward the interpretative "how would this tool sound" character
that the specimen illustrations carry. Accents as a substitute would have to be
randomized to avoid caricature, which removes the interpretation altogether.
The per-project voice direction above is therefore not pursued. The runtime
work (pinned runners, manifests, reproducibility) stays available outside this
repository.

## Next path: cloned name voice and ambient scene

Not started. Recorded as direction only.

1. **Name reading:** one voice, cloned from a friend's recording, reads the plain
   project name. This needs that person's documented, informed consent for
   cloning and for publication under this repository's terms, and a cloning
   model whose license permits it. The existing rules still apply: no imitation
   of identifiable public people, and the original text stays visible.
2. **Ambient scene:** an audio-effects pipeline places a quiet background scene
   beneath the name, such as bird song, wind, a busy office, a factory or a
   train station. The scene is chosen from an interpretation of the tool's vibe,
   so the interpretative layer moves from the voice to the setting. Every scene
   source needs a license compatible with publication here; generated, recorded
   and library sounds each need a provenance record.

Pronunciation, provenance, accessible playback and no-autoplay rules from this
plan carry over. Owner pronunciation guesses so far: OpenRA "Open R A",
OpenSCAD "Open S-CAD".

## Identity, provenance and review requirements

Design the audio schema in a later implementation PR after the pilot; the list
below is required information, **not an invented existing manifest contract**.
Reuse the catalog's complete canonical-URL-derived project ID and exact URL.
Cross-category entries share recordings. Display-name or pronunciation changes
must invalidate affected clips without changing project identity.

Retain:

- Official source documents, verified Git commit revisions where available, or
  retrieval date/content hash for other sources; the actual material consulted.
- The original per-project voice description, complete conditioning prompt,
  spoken text, pronunciation choices and neutral/character designation.
- Model/checkpoint revision, runtime/settings/seed where available, rights review
  and any synthetic reference audio used to preserve a designed voice.
- Original generated audio and final served derivative, hashes, encoding, duration,
  trim/processing history, and text/source version association. Hash the decoded
  samples as well as the file: container metadata can change a file hash without
  changing the audio.
- Actual listening reviewer identity (identify AI reviewers honestly), inspection
  date, technical and content findings, and explicit audio publication status.

Do not claim individual owner listening or reuse illustration display approval as
permission to mark audio reviewed. Preserve failed auditions separately from
published clips. Replace an accepted voice only through an intentional revision;
never silently regenerate every recording on a build or alter unrelated artwork.

## Pilot exit and remaining decisions

Before implementation, record listening results and select a license-compatible
backend, the owner's actual local hardware/runtime route, neutral fallback,
pronunciation policy, retained artifact storage, format/size budget and regeneration
policy. Determine whether distinct voices remain consistent across a name and a
Function summary. Estimate measured generation time and storage from the pilot,
then project catalog-scale cost; do not infer affordability from a chat subscription.

A subsequent scoped PR can define schema, validation, asset handling and accessible
playback. Review missing audio, failed loads, repeated play/stop, voice switching,
drawer closure, mobile layouts and standalone behavior. No catalog-wide generation,
service subscription or live backend is part of this documentation proposal.
