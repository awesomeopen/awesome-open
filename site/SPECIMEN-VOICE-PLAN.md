# Specimen voices: proposed feature and audition plan

Status: **proposal, not implemented**. Research checked 2026-10-18. No audio has
been generated or auditioned for this plan; no model ranking is established.
This document does not install a model, enable a service, authorize spending,
change the site, or extend existing artwork approval to audio.

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

## Short-name generation experiment (not yet run)

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
| [Maya1](https://huggingface.co/maya-research/maya1) | Llama-style autoregressive model with SNAC discrete audio codes, text-described voices and an Apache-2.0 model declaration | Superiority for isolated names, artifact rate, local hardware performance and reproducible character |
| [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) | Discrete multi-codebook language-model approach, voice design and reuse of a generated voice reference | Claimed short-input instability or a required carrier phrase |
| [VoxCPM2](https://github.com/OpenBMB/VoxCPM) | Continuous-latent diffusion-autoregressive voice design; Apache-2.0 code/weights. Its [paper](https://arxiv.org/html/2606.06928v1) reports general TTS/control evaluations | Claimed poor one/two-word stability, mandatory warm-up and performance on the owner's machine |
| [Breeze TTS 2](https://github.com/breezeblue-ai/breeze-tts#license-and-responsible-use) | Voice design and Qwen3-TTS-derived audio tokenizer; code Apache-2.0, but weights, derivatives and self-hosted outputs restricted to research/non-commercial use | Short-name padding benefit and suitability for public catalog audio; documented Linux/CUDA runtime is not evidence of working Apple Silicon support |

Breeze is a **licensing-gated research candidate**, not an approved production
choice. A hosted-service license does not automatically license self-hosted output.
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
duration, generation time and all failures, not just the selected best output.
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
  trim/processing history, and text/source version association.
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
