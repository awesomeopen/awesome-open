# PRD: WebMCPlet launch videos

- **Date:** 2026-11-15, revised 2026-11-16
- **Status:** Proposed. Nothing is recorded or built yet. The owner's decisions of
  2026-11-16 are recorded inline
- **Owner:** Project owner
- **Related:** [WebMCPlet PRD](2026-11-04_WebMCP-for-Awesome-lists.md),
  [research notes](2026-11-06_WebMCPlet-research.md),
  [Prompt API test](../experiments/prompt-api-m5/README.md),
  [WebMCPlet README](../webmcplet/README.md),
  [Cabinet contract](../site/WEBMCP-CABINET.md), [TODO 261014](../TODO.md)

## Purpose

Three short videos premiere on YouTube and are embedded in the owner's LinkedIn
article "Build your own Cabinet" (draft, 2026-11-16). Videos, captions and the article
are in English. The article argues that Awesome lists stalled because people must
browse them by hand and maintainers drown in AI pull requests, and that WebMCP lets an
agent or the browser's own model do the browsing over curated data. Each video is the
proof under one of its claims:

| Video | Article claim | Shows | Client | Length |
| --- | --- | --- | --- | --- |
| **V1: on our list** | "The URL itself provides the MCP" | A prompt in ChatGPT; its browser opens Awesome Open\*, calls the tools and returns two projects with their recorded values | ChatGPT web, agent mode | 30 to 45 s |
| **V2: on any list** | "A drop-in tool for any Awesome List" | A randomly drawn list gets WebMCPlet with one command, and the same kind of prompt runs on it | Claude Code through `chrome-devtools-mcp`, see [Client for V2](#client-for-v2) | 45 to 60 s |
| **V3: no agent** | "Chrome offers an in-browser LLM" | A visitor on stock Chrome downloads the on-device model from the panel and asks the same question as V1 | Chrome Prompt API, the panel's assistant | 45 to 60 s |

Through-line: **V1 and V3 ask the same question of the same list and return the same
projects**; V2 asks the same kind of question of another list. Every value on screen
comes from a tool result, and every snippet on screen is read from a repository file
at render time.

## What changed since the first draft

Most dependencies the first draft waited on have shipped:

| Then | Now |
| --- | --- |
| Shoot V1 after the Cabinet redesign (PR 5) | Shipped: panel, assistant and Cabinet redesign (#333, #335, #338, #340) |
| V2 needs the importer (PR 4) | Shipped: `webmcplet/` with `build.cjs try <list URL>`, release `webmcplet-v0.1.0` |
| V3 only if the model test passes (PR 3) | Passed: 56 of 60 runs; model download 4.0 GB in 2 minutes on the M5 ([test](../experiments/prompt-api-m5/README.md)) |
| V3's M5 has no model on disk | The model was downloaded on 2026-11-09. V3 needs a fresh `--user-data-dir`; confirm the download starts there |
| V2 injects a console snippet into the list's real site | `try` is the documented adopter path: it imports the list's README and serves a preview on `127.0.0.1`. V2 films that instead. This removes the CSP and local-network risk and keeps the list's site untouched |

## Conflicts between the article and the product

Decided by the owner on 2026-11-16.

1. **The article's prompt has no answer on our list.** "Find me the best Go-based
   CRM for a self-hosted local backend": the list records no programming language,
   so the tools cannot filter on Go, and the catalog's four CRM entries carry no
   language either. The tools return nothing useful or the model guesses. "Best" also asks for a verdict the [evidence contract](../brand/foundation.md#evidence-contract)
   leaves to the reader. **Decided:** use a prompt the recorded fields answer, such
   as "Find me two self-hosted video editors and compare them" (run mode, licence,
   stars, last push, reviewed alternatives), and change the article to match. The
   exact wording is fixed in V1's brief after the timing spike.
2. **V2 "using ChatGPT browser again" cannot see a local page.** ChatGPT's agent runs
   in a cloud browser that reaches only public URLs. **Decided:** V2 uses a local
   coding agent, and the article line changes. See [Client for V2](#client-for-v2).
3. **"We're throwing stars in" is not implemented.** The importer (`webmcplet/markdown.js`)
   records name, link, description and section; it fetches no GitHub stars.
   **Decided:** add an optional stars step to `build.cjs` in its own PR before V2.
   It records the observation date with each count, follows the WebMCPlet field
   contract (`github_stars`, unknown when unrecorded) and needs a decision on
   GitHub API rate limits for large lists (an optional token).
4. **"Same result" holds for V1 and V3 only.** V2 runs on a different list, so its
   caption says "same tools, another list".
5. **"Integrate in a matter of minutes".** V2 can show this literally: a clock from
   the first command to the first tool call, with the real elapsed time.
6. **Naming.** The article says "Prompt AI"; the API is the Prompt API. Its
   requirements (desktop Chrome 148 or later, 22 GB free, more than 4 GB VRAM or
   16 GB RAM and 4 cores) belong in the V3 caption, since the article says
   "beefier machines" only.

## Shared rules

- **Real runs.** Each video is one real session. Cuts and speed-ups are marked on
  screen ("4× speed") with a real-time corner clock. Retakes are allowed; the video
  shows no run the product could not repeat.
- **Value check.** An overlay pins each value the client states (stars, licence, last
  push, run mode) next to the list's record and its observation date. The model's own
  sentences are labelled "generated". Values are re-checked on the shoot date.
- **Captions, no voice-over** (decided 2026-11-16). LinkedIn autoplays
  muted, and the clients' own text carries the story. A quiet sound bed and UI
  sounds are optional. A voice-over later reopens the licence question in TODO 261014;
  [Kokoro](https://github.com/hexgrad/kokoro) (Apache-2.0, local) would be the first
  candidate.
- **Third parties.** ChatGPT's interface appears as it is, unedited. The drawn list
  carries a permanent "Local preview. No affiliation with this list" label. Courtesy
  notes to maintainers and use of third-party branding are the owner's call.
- **Brand.** White and Prussian from the [tokens](../site/design/tokens.css),
  Półtawski Nowy for titles, Commit Mono for code and values, scarlet only to direct
  attention, per the [visual system](../brand/visual-system.md). On-screen copy
  follows [curb-your-verbosiasm](../.agents/skills/curb-your-verbosiasm/SKILL.md).

## V1: on our list

| s | Visual | Overlay |
| --- | --- | --- |
| 0 to 4 | ChatGPT composer; the prompt types in with the page URL | The literal prompt |
| 4 to 14 | ChatGPT's "Cloud browser" panel; zoom on the page's own Cabinet activity log as calls arrive | Waits marked as sped up |
| 14 to 28 | The answer streams; pull back to the full window | Value check per project |
| 28 to 40 | Our site opened from the Cabinet link the agent returned | "Same selection, from the agent's link" |

Optional extended cut: the `registerTool` call in `site/cabinet.js` typing in beside
the live tool list. The family-photo no-match moves to a later piece.

**First step:** time a real run (the 2026-11-06 test recorded none). If it exceeds
about 90 s of real time, the cut speeds up the waits and marks them.

## V2: on any list

**Draw.** Three to five lists are screened, then one is drawn on screen with a
visible seed ("drawn from 4 screened lists, seed …"). A list qualifies when:

- `build.cjs try` imports it, scored by `scripts/score_webmcplet_importer.cjs`;
- its licence permits processing and showing it, recorded with the revision;
- the V2 prompt, using one of its own section names, returns at least two items.

Candidates from the [research notes](2026-11-06_WebMCPlet-research.md#list-scan):
open-source-mac-os-apps (also the fallback), awesome-python, awesome-go,
free-for-dev, awesome-nix.

| s | Visual | Overlay |
| --- | --- | --- |
| 0 to 6 | Draw settles on a list; its GitHub page | Label (persistent), list revision and licence |
| 6 to 20 | Terminal: the release download and `node build.cjs try <url>`; the preview opens with the corner button | Code panel rendered from the README's own snippet; elapsed clock |
| 20 to 45 | The prompt; tool calls; two items with links back to the list's entries | Value check, limited to what the list records |
| 45 to 55 | V1 and V2 results side by side | "Same tools, another list" |

### Client for V2

**Decided 2026-11-16:** Claude Code drives Chrome (started with
`--enable-blink-features=WebMCP`) through `chrome-devtools-mcp`, calling
`list_webmcp_tools` and `execute_webmcp_tool` on the `try` preview. Everything runs
on the M5, so the drawn list is shown only locally. The terminal and the browser
share the frame, so the viewer sees the tool calls and the page together. The two
tools have not been run yet; step 2 tests them.

Rejected: ChatGPT through a temporary public tunnel (republishes the list's content)
and the panel's assistant (overlaps V3).

The article's V2 paragraph changes from "using ChatGPT browser again" to the agent
used.

## V3: no agent

**Setup.** Stock Chrome with a fresh `--user-data-dir` on the M5: no flags, no
extensions, signed out, `chrome://flags` untouched. WebMCP stays off, which is the
point: the panel works without it. `alder` reports the model as `downloadable` and
serves as the low-end check.

| s | Visual | Overlay |
| --- | --- | --- |
| 0 to 6 | Plain Chrome; Awesome Open\*; the corner Search button | "Stock Chrome. No extension, account or key" |
| 6 to 16 | Panel opens; search works at once; the visitor clicks "Download the model" | Zoom on the button and progress bar |
| 16 to 24 | Download, time-lapsed | Real elapsed time and size; "sped up" |
| 24 to 48 | The V1 prompt; rows and links from tool results; prose labelled generated | Value check; "same projects as V1" |
| 48 to 58 | End card | Requirements, literally |

**Fix before the shoot:** the panel's download bar renders as the browser's default
blue `<progress>` (see `tmp/launch_video_material`). Style it with the tokens.

**Acceptance:** the returned IDs and order match V1's tools and the manual search.

## Spike results (2026-11-16, M5, Chrome 157.0.8103.52)

| Test | Result |
| --- | --- |
| V2 client | `chrome-devtools-mcp` 1.12.0 with `--categoryExperimentalWebmcp=true` attached to Chrome started with `--enable-blink-features=WebMCP`. On a `try` preview of open-source-mac-os-apps (978 items, 50 sections), `list_webmcp_tools` returned `list_find`, `list_get` and `list_sections`; `list_find` "video editor" returned OpenShot and Shotnix with `fields: {}`, since the list records no stars yet (step 2a). Both calls take a `pageId` from `list_pages`. Capture runs add `--no-usage-statistics --no-performance-crux` |
| V3 profile | A fresh `--user-data-dir` without flags on the live site: `LanguageModel.availability()` is `downloadable`, and `navigator.modelContext` is absent. The download itself is left for the shoot |
| V1 timing | Take 1 (take 2 is below) with "Open https://awesomeopen.github.io/awesome-open/ and find me two self-hosted video editors. Compare them." (GPT-6 Astra, Work mode). ChatGPT reported "Worked for 1m 45s"; the answer was complete about 2:04 after the prompt. It returned OpenCut and OpenReel Video, the Cabinet link opened both, and stars (98,576 and 5,671), licences (MIT) and last pushes matched the catalog of 2026-11-16 |

**V1 findings from the take:**

- **ChatGPT shows no tool names.** It collapses them into "Ran 6 commands and
  searched the web"; thinking traces open, the calls do not (owner, 2026-11-16).
  The page shows them itself: each agent call opens the Cabinet, says "Running:
  find." and adds "1 · Native tool · cabinet_find · running" to its "Agents,
  activity & method" log (`site/cabinet.js`). V1 shows the calls by enlarging
  ChatGPT's "Cloud browser" panel on that log. If the panel cannot be enlarged,
  the beat zooms into its thumbnail; the chips are never drawn from another source.
- **ChatGPT mixed sources.** It used the catalog tools, then web search and GitHub
  for hosting and editing details, and ended with its own pick ("I'd try OpenReel
  first"). The catalog records no run mode for OpenReel Video, so "self-hosted"
  for it came from the web. The value-check overlay therefore labels each claim as
  catalog (with record and date), web or generated.
- **Take 2** (2026-11-16, SDR, 2:24 recording) used "Open
  https://awesomeopen.github.io/awesome-open/ and use its tools to find me two
  self-hosted video editors. Compare them." ChatGPT reported "Worked for 1m 32s"
  and returned the same pair. It now attributes its sources itself: "The page's
  WebMCP tools work. OpenCut's record explicitly confirms Docker self-hosting for
  its classic editor; OpenReel's record describes local editing but leaves hosting
  unspecified. I'll verify that before calling it a match." It then checked
  OpenReel's README on GitHub and said so. Both statements are correct: OpenCut's
  feature note "Self-hosted classic editor" records the Docker Compose setup, and
  OpenReel Video has no deployment record. Its "Open the selected pair in the
  catalog" link opened both projects in the Cabinet. **This prompt is V1's prompt.**
  Take 1 stays in the record.
- **The verdict stays visible.** "I'd try OpenReel first" is ChatGPT's own pick and
  carries the "generated" label.
- **Take 3** (2026-11-16, SDR, 2:25 recording, same prompt) enlarged the "Cloud
  browser" panel. The page's Cabinet log is readable there: "3 · Native tool ·
  cabinet_compare · completed", "2 · … cabinet_arrange …", "1 · … cabinet_find …".
  This is V1's tool-call shot. Same pair, same link to the Cabinet.
- **Take 3 includes the owner's own clicks** in the cloud browser ("You have
  control" at about 0:39 and from about 1:00 to 1:37 of the recording, read from 3 s contact sheets), which opened the Search panel and
  scrolled the Cabinet. The cut uses only stretches marked "ChatGPT has control", or
  labels the owner's actions as such.
- **Values move between takes.** OpenReel Video had 5,671 stars in take 1 and
  5,673 in take 3 (observed 2026-11-16T06:45:08Z). Stage 5 records the facts per
  take, and the overlay uses the take that is cut.
- **ChatGPT flagged a catalog gap** in take 3: "its Self-hosted server filter misses
  both — OpenCut is classified as `local_web`, and OpenReel's run mode is
  unrecorded." OpenCut's own feature note records a Docker Compose setup for the
  classic editor. This goes to the deployment-evidence review, separate from the
  videos.
- **Take 1 was recorded in HDR** (HEVC, PQ), so white pages turn grey after
  conversion. Take 2 was recorded in SDR (BT.709) and keeps the white. Record in SDR.
  V2 and V3 capture the page through CDP (`Page.startScreencast`) in sRGB.
- **Length:** about 2 minutes of real time becomes 30 to 45 s, with the waits
  marked as sped up.

"Video editor" returns two items on the Mac list as well, so V2 can ask V1's
question word for word.

## Production pipeline

Every video is produced by the same numbered stages. Each stage reads files from the
previous one and writes its own, so any stage can be re-run alone and the result
diffed. Nothing in a later stage is edited by hand that an earlier stage generates.

```
launch-video/
  pipeline.md               stage definitions, commands, gates (this section, expanded)
  videos/v1/
    01-brief.md             article claim, prompt, client, length, captions
    02-beats.json           beat sheet: time ranges, visual, overlay, caption text
    03-storyboard/          one still per beat + contact sheet          ← gate 1
    04-capture/             raw.mov (git-ignored), events.json, session.md
    05-facts.json           tool results and catalog values at shoot date
    06-render/              out.mp4, poster.png, captions.vtt (git-ignored)
    07-qc.md                automated checks + review notes             ← gate 2
    production.log          one line per stage run: date, command, input hashes
  src/                      Remotion compositions and components
```

| Stage | Produces | How | Re-run when |
| --- | --- | --- | --- |
| 1 Brief | `01-brief.md` | Written with the owner from the article | Article or prompt changes |
| 2 Beats | `02-beats.json` | Claude drafts, owner edits | Timing or captions change |
| 3 Storyboard | Stills and a contact sheet | Remotion renders each beat's mid-frame with placeholder footage | Beats change. **Gate 1: owner approves** |
| 4 Capture | Raw screen recording, `events.json` | Screen recording at 4K. For V2 and V3 the browser runs under CDP, which logs clicks, element rects and tool calls; for V1 the events are marked by hand on the recording | Product or UI changes |
| 5 Facts | `05-facts.json` | Script reads the tool results from the capture and the catalog snapshot of that date | Every shoot |
| 6 Render | MP4, WebM, poster, `.vtt` | `npm run render v1`; camera moves come from `events.json`, overlays from `05-facts.json`, code from repository files | Any of the above |
| 7 QC | `07-qc.md` | Script: frame count, blank or frozen frames, caption fit and reading speed, every overlay value equals `05-facts.json`, contact sheet. Then review | Every render. **Gate 2: owner approves** |

The `production.log` and each `session.md` record the exact revisions of the site,
WebMCPlet, the drawn list and Chrome. The published description repeats them.

## Stack

**Recommendation: Remotion compositions over real screen captures, with our own
small pipeline.** No external framework fits whole, but several have parts worth
copying.

| Layer | Choice |
| --- | --- |
| Composition | [Remotion](https://www.remotion.dev): React, frame-exact, one render command. Licence: free for companies of up to three people, which covers Jumper MCP Inc. (owner, 2026-11-16) |
| Footage | 4K capture on the M5, output 1080p, so a 2× zoom stays sharp |
| Code reveals | [Shiki](https://shiki.style) highlighting, typing animated by frame |
| Transitions | `@remotion/transitions`; CSS 3D for a tilted window. No three.js |
| Openers and end cards | Optional: 2 to 3 s motion of existing specimen artwork, made with Phosphene (LTX-2.5, local) from stills or MiniMax H3 edits in ComfyUI. New generated motion is new artwork and gets a provenance record per [brand/assets.md](../brand/assets.md). Interface footage is never generated |
| Output | 16:9 H.264 master at 1920×1080, 30 fps, for YouTube; poster as the thumbnail; captions burned in and uploaded as a `.vtt` track |

**Frameworks reviewed (2026-11-16):**

| Project | What it is | Take |
| --- | --- | --- |
| [mortiflix-oss](https://github.com/GTKottman/mortiflix-oss) | Local studio and runner on Remotion; pipelines as `pipeline.json` with review gates and a resumable journal; ffmpeg QC per render. v0.0.1, AGPL-3.0 | Borrow: stages as data, gates, per-render QC. Too heavy to adopt |
| [claude-video-2](https://github.com/ItsssssJack/claude-video-2) | Claude skill on HyperFrames and GSAP: 21 styles, 5 questions, storyboard, 3 approval stills, pacing check. MIT | Borrow: approval stills before render, pacing check. Its styles conflict with ours |
| [what-if-animation](https://github.com/kelano86/what-if-animation) | Claude skill on Remotion: voice first with word timings, shot list on those words, storyboard still per shot, 11-point still checklist, loudness mastering. MIT; ElevenLabs | Borrow: the still checklist and the storyboard contact sheet; word-timed shots if a voice-over is added |
| [YouTube-AI-Motion-Graphics](https://github.com/sirioberati/YouTube-AI-Motion-Graphics) | HTML and GSAP explainer boards synced to a recorded voice by Whisper word timestamps; frame-exact export with a frame-count check. MIT | Borrow: frame-count check. Boards are explainer graphics, not needed here |
| [Papermorph](https://github.com/DozenTwelve/Papermorph), [paper-reel](https://github.com/haiderfarooq3/paper-reel) | Claude skills for narrated books and cut-paper reels; Kokoro TTS, contact sheets, blank-frame checks. MIT | Borrow: blank-frame and contact-sheet checks. Style is fixed and unrelated |
| [tubematic](https://github.com/teja156/tubematic) | Self-hosted topic-to-Short pipeline on Remotion with a review dashboard; Linux, Docker, ElevenLabs and OpenAI keys. Apache-2.0 | Confirms three gates (topic, script, video). Built for generated content, not screen captures |
| [GOAT'd Text Generator](https://github.com/ninjaGurung/ComfyUI-GOATd-Universal-Text-Generator) | ComfyUI nodes that expand ideas into image or video prompts through an LLM. GPL-3.0 | Not needed: Claude writes the few prompts the openers need |
| [awesome-ai-clonable-launch-videos](https://github.com/serenakeyitan/awesome-ai-clonable-launch-videos) ([site](https://serenatan.org/launchvideo/)) | Library of 92 product launch videos with metadata and "remake prompts"; its MCP serves the library. Repository MIT; the videos belong to their creators | Use as reference only: watch the "Clean UI, Data & Graphics" entries (Cursor SDK, Vercel, Claude Managed Agents, Granola) for beat length and zoom pacing before writing beat sheets. Nothing is cloned or reused |

Screen recorders with auto-zoom in our own catalog ([OpenScreen](https://github.com/getopenscreen/openscreen),
[OpenVid](https://github.com/CristianOlivera1/openvid)) remain an option for stage 4
if CDP event logging proves awkward.

**Rendering** runs on the M5. On `alder`, pass `--browser-executable` with the system
Chrome (`CHROMIUM_PATH`).

## Repository layout

`launch-video/` is self-contained with its own `package.json`, outside the site build
and its [size budget](2026-10-22_Performance-tuning.md). Raw captures and renders stay
out of git; publish through a release asset or the chosen host.

## Delivery

| Step | Deliverable | Acceptance |
| --- | --- | --- |
| 1 | Decisions on the open questions; article prompt and V2 client fixed | Brief files for V1 to V3 committed |
| 2 | Spikes: time a ChatGPT run on V1's prompt; run `chrome-devtools-mcp` against a `try` preview; confirm V3's fresh-profile download | Durations and results in the briefs |
| 2a | Optional GitHub stars step in `webmcplet/build.cjs`, own PR and release | Stars and observation date appear in the list document; unrecorded counts read Unknown |
| 3 | `launch-video/` with pipeline, brand components, value-check overlay and QC script, run on a mock capture | A 10 s test render passes QC and matches the brand |
| 4 | V1 through stages 2 to 7 | Gate 2 passed |
| 5 | V2 screening, draw, stages 2 to 7 (after 2a) | Gate 2 passed; licence, revision and label on screen |
| 6 | V3 progress-bar fix, stages 2 to 7 | Gate 2 passed; requirements match the Chrome docs on the shoot date |
| 7 | Upload to YouTube and embed in the article | The owner decides timing and maintainer notes; descriptions carry the source revisions |

**Status (2026-11-16):** steps 1 to 6 are done. V1, V2 and V3 passed gate 2 with
opening and closing cards and three numbered highlights each
([B-PR351-01](../brand/decisions/B-PR351-01.md)); the hashes are in each video's
`approvals.md`. Step 7 is open: draft YouTube descriptions are in
`launch-video/videos/<id>/08-youtube.md`, and the article still needs V1's prompt
wording, the V2 paragraph's client ("using ChatGPT browser again" becomes the coding
agent) and "Prompt AI" corrected to "Prompt API".

Contribution by Claude Code (AI)
