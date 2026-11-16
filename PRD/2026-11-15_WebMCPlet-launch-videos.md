# PRD: WebMCPlet launch videos

- **Date:** 2026-11-15
- **Status:** Proposed. Nothing is recorded or built yet
- **Owner:** Project owner
- **Baseline:** branch `docs/webmcplet-prd`, after `52a856f`
- **Related:** [WebMCPlet PRD](2026-11-04_WebMCP-for-Awesome-lists.md),
  [research notes](2026-11-06_WebMCPlet-research.md),
  [Cabinet contract](../site/WEBMCP-CABINET.md), [TODO 261014](../TODO.md)

## Purpose

Three short videos show that a curated list becomes searchable and comparable by an
agent once its page exposes WebMCP tools, and by the visitor's own browser model
when no agent is involved. The owner's launch text carries the hook: Awesome lists
lost their appeal, and WebMCP brings it back with curated data plus agent search and
comparison. The videos show the mechanism working, in escalating reach: a cloud
agent on our list, a local agent on someone else's list, then no agent at all.

| Video | Shows | Length | Agent |
| --- | --- | --- | --- |
| **V1: it works on ours** | A typed prompt in ChatGPT; its browser opens Awesome Open\*; it calls the Cabinet tools and returns a comparison | 20 s hero, 40 s extended | ChatGPT web UI (worked 2026-11-06) |
| **V2: it works on yours** | One list drawn from a pre-screened pool gets WebMCPlet injected in our own browser; the same kind of query runs on it | 45 to 60 s | Coding agent through DevTools, see [Agent for V2](#agent-for-v2) |
| **V3: it works with nothing** (finale) | A casual Chrome user opens Awesome Open\*, accepts the on-device model download, and queries the Catalog through the in-page assistant | 60 to 75 s | Chrome's built-in model (Prompt API) |

All videos show code that runs. Every snippet on screen is read from a repository
file at render time, so the picture cannot drift from the implementation.

## Reconciling earlier plans

| Earlier plan | Source | Resolution |
| --- | --- | --- |
| About 90 s demo recording on the M5: local assistant on "video editor", family-photo no-match, same script on the Mac list, then an agent on the same tools | [WebMCPlet PRD, Delivery](2026-11-04_WebMCP-for-Awesome-lists.md#delivery), PR 6 | Replaced by V1 and V2. Its no-match journey becomes the last beat of the V1 extended cut; its Mac-list step becomes the fallback draw for V2. The owner-review gate stays |
| Product video with a narrator discovering the "Áwesome lists" history | [TODO 261014](../TODO.md) | Stays a separate, later piece. It covers the whole site and uses a narrator; these two cover one feature and need none. The Remotion project, fonts and overlay components carry over. The TTS licence correction in that entry still applies |
| Voice work: cloned name voice and ambient scene | [TODO 261018](../TODO.md), [voice plan](../site/SPECIMEN-VOICE-PLAN.md) | Not used. All three videos carry captions and no voice-over, which also works muted on social feeds |
| Mac list as the outside fixture | WebMCPlet PRD, Journeys | One member of the V2 pool, and the fallback if a draw fails its checks |
| "Injected only in our own browser", "local demo with no affiliation", no deployment to other sites, no contact with maintainers without the owner | WebMCPlet PRD, Delivery and Out of scope | Kept. V2 carries a permanent on-screen label and the owner decides about a courtesy note to the drawn list's maintainer before publication |
| Prompt API as a separate demo | [WebMCPlet PRD, Two ways to use the tools](2026-11-04_WebMCP-for-Awesome-lists.md#two-ways-to-use-the-tools) | Becomes V3. The PRD keeps the Prompt API only if the model test (PR 3) passes, so V3 exists only on a pass |
| Query wording | WebMCPlet PRD, Journeys (revised 2026-11-15) | V1 uses "Find a video editor for me by comparing two" with the page URL added, since ChatGPT must be told where to look (the research prompt did this) |

## Findings that shape the plan

1. **ChatGPT's cloud browser cannot see our injection.** It loads the real public
   site, so V2 needs a client running in our own browser. This is why V2 and V1 use
   different agents.
2. **A real ChatGPT run is unlikely to fit 10 to 20 s.** The 2026-11-06 test did not
   record its duration. Time it on the first take. V1 keeps real time in a corner
   clock and marks every cut or speed-up on screen ("waiting, 4× speed"). The hero
   cut targets 20 s of screen time.
3. **"Accurate" needs a visible check.** In the ChatGPT test, tool values matched the
   catalog, and the model added its own judgment ("the more immediately informative
   choice"). The overlay shows each value next to its catalog record and date, and
   labels the model's own sentence as generated. This follows the PRD's rule that
   tool rows and model prose stay separate. Re-check stars, licences and push dates
   on the shoot date.
4. **The Cabinet interface is due for a redesign** (PRD 5). V1 footage of the current
   interface becomes outdated. Shoot V1 after PR 5.
5. **V2 needs the importer** (PR 4), so it follows it. The snippets V2 shows (script
   tag, build command) do not exist yet and appear only once they do.
6. **Cross-origin loading is a risk for injection.** A console-injected script that
   fetches JSON from `localhost` can hit the target page's CSP or Chrome's local
   network permission prompt. Inline the JSON in the injected snippet, or use a Local
   Override in DevTools, and test both on each pool list.
7. **"Needs nothing" has limits the video must show.** The Prompt API needs desktop
   Chrome 148 or later, at least 22 GB free, and either more than 4 GB VRAM or 16 GB
   RAM and 4 cores, per the research notes. It needs no extension, account or key. The
   end card states the requirements literally. V3 claims "no install, no account, no
   key", and nothing broader.
8. **Chrome shows no download prompt of its own.** Per the PRD, the panel's assistant
   appears when the model is available or downloadable, and the download starts only
   on an explicit click in the panel. V3 films that button, not a browser dialog.
9. **V3 must run flag-free on a stock profile.** Native tool use in the Prompt API
   needs a flag, so the in-page assistant relies on structured output
   (`responseConstraint`) and dispatches registered actions itself. Capture on a clean
   profile and show that the flags page is untouched.
10. **WebMCP is off by default in Chrome 156.** Launch the capture browser with
   `--enable-blink-features=WebMCP` and show nothing that implies visitors need it
   for the panel search.

## V1: it works on ours

**Beats (20 s hero):**

| s | Visual | Overlay |
| --- | --- | --- |
| 0 to 3 | ChatGPT composer; the prompt types in | Caption: the literal prompt |
| 3 to 8 | ChatGPT opens its browser on Awesome Open\*; zoom into the tool-call lines | Chips as calls appear: `cabinet_find`, `cabinet_arrange`, `cabinet_compare` |
| 8 to 14 | Answer streams; camera pulls back to full window | Per-value check: stars, licence, push date against the catalog record, with observation date |
| 14 to 20 | Cut to our site opened from the shareable Cabinet URL showing the same two projects | "Same selection, opened from the link the agent returned" |

**Extended cut (40 s)** adds the code reveal (the `registerTool` call in
`site/cabinet.js` typing in beside the live tool list) and the family-photo query
returning a clear no-match with no unrelated project named.

The shareable URL beat reuses the PRD's links-back decision: a person on an agent's
cloud browser never sees the page, so the link is how the viewer reaches it.

## V2: it works on yours

**Draw.** A pool of 5 to 8 lists is screened before the draw. A list qualifies when
all of these hold:

- the entry format is `- [name](url) - description`, or it ships structured JSON;
- the licence permits showing and processing it (CC0 or equivalent), recorded with
  the revision;
- the importer reproduces its entries, scored as in the acceptance list test;
- the V2 query returns at least two matches.

Candidates from the [research notes](2026-11-06_WebMCPlet-research.md#list-scan):
open-source-mac-os-apps, awesome-python, awesome-go, free-for-dev, awesome-nix and
awesome-mac (rights conflict to resolve first). The draw uses a seed shown on screen
("drawn from 6 pre-screened lists, seed …"), so the randomness is real and the
screening is disclosed.

**Beats (about 50 s):**

| s | Visual | Overlay |
| --- | --- | --- |
| 0 to 6 | Draw animation settles on a list; browser opens its real site | "Local demo. No affiliation with this list" (persistent) |
| 6 to 20 | Two-line integration typed: build step output and script tag, rendered from the real files; the page reloads with the corner button | Code panel beside the browser; zoom to the new button |
| 20 to 40 | Query typed to the agent; tool calls appear; result rows with links back to the list's own entries | Same value-check overlay as V1, with fields limited to what the list supplies |
| 40 to 50 | Pull-back: V1 and V2 results side by side | "Same tools, different list" |

The query follows V1's shape: "Find a [category] for me by comparing two". The
category comes from the drawn list's own section names.

### Agent for V2

| Option | Fit | Condition |
| --- | --- | --- |
| Coding agent through `chrome-devtools-mcp` (`list_webmcp_tools`, `execute_webmcp_tool`) | Works today with page tools; shows tool calls in a terminal | The two named tools have not been run yet (research notes) |
| ChatGPT desktop | Same agent as V1 | Untested |

Default: the DevTools route. The panel assistant belongs to V3, so the three videos
show three different clients. If the owner wants ChatGPT's web UI in V2, the alternative is a public mirror of a CC0 list
under our own organization with the script added. That breaks the "their real site"
premise and needs the owner's decision.

## V3: it works with nothing

**Setup.** A clean Chrome profile on the M5, where the model is not on disk (research
notes, 2026-11-06), so the download is real. No flags, no extensions, signed out. The
`alder` machine reports the model as `downloadable` and serves as the low-end check
that the claim holds there.

**Beats (about 70 s):**

| s | Visual | Overlay |
| --- | --- | --- |
| 0 to 8 | A plain Chrome window; the visitor lands on Awesome Open\*; hovers the corner button | Caption: "Stock Chrome. No extension, account or key" |
| 8 to 20 | Panel opens; search works at once; the assistant offers the model download; the visitor clicks it | Zoom to the download button and progress bar |
| 20 to 30 | Download progress, time-lapsed | Real elapsed time and size on a clock; "sped up" marked |
| 30 to 55 | The visitor types "Find a video editor for me by comparing two"; the assistant answers; rows and links come from tool results, the model's prose is labelled generated | Same value-check overlay as V1 and V2 |
| 55 to 70 | Pull-back to all three results; end card | Requirements: desktop Chrome 148+, 22 GB free, 16 GB RAM and 4 cores or more than 4 GB VRAM |

**Code reveal.** The `LanguageModel.availability()` and `create()` calls with the
user-activation gate, and the deterministic check that rejects any project the tools
did not return, read from the shipped panel source.

**Acceptance.** Footage is one unbroken stock-profile session apart from the marked
time-lapse. The query returns the same IDs and order as the manual search and V1's
tools. Record the model download size and duration at the shoot.

**Risks.** The model may answer slowly or invalidly on camera. Retakes are allowed
when each take is honest; the video shows no run the product could not repeat. If the
PR 3 threshold fails, V3 is dropped and the two-video plan stands.

## Stack

**Recommendation: Remotion, with real screen capture as the footage.**

| Layer | Choice | Why |
| --- | --- | --- |
| Composition | [Remotion](https://www.remotion.dev) 4.0.543 (npm, checked 2026-11-15): React components, frame-exact, scripted | Overlays, zooms, code reveals and captions are components; the whole video re-renders from one command after any change |
| Footage | Capture at 4K on the M5 (Chrome 156, retina) and output 1080p | A 2× zoom stays sharp |
| Camera moves | A JSON event log from the capture (cursor positions, click targets, tool-call timestamps, element rects) drives scale and translate transforms in Remotion | Zoom in on a click or tool call and pull back for the answer, without hand-keyframing |
| Code reveals | [Shiki](https://shiki.style) highlighting in a Remotion component, typing animated by frame; source read from repository files at render time | What the viewer sees is the code that ran |
| Depth and flash | CSS 3D transforms for a tilted browser window and layered callouts; `@remotion/three` for at most one hero shot (V2 draw) | Three.js costs render time and needs WebGL flags in headless Chrome; take it only where CSS depth falls short |
| Transitions | `@remotion/transitions` | Stock cuts and slides, no custom code |
| Output | MP4 (H.264) master at 1920×1080 and 30 fps, WebM, a poster frame and `.vtt` captions | Muted autoplay works with burned-in captions; the `.vtt` serves the docs page |

**Look.** White and Prussian from the [tokens](../site/design/tokens.css), Półtawski
Nowy for titles, Commit Mono for code and values, scarlet only to direct attention.
"Moderately flashy" comes from camera movement, typed code, glass-like callout panels
and the draw animation. No theme lottery, and no parallax or marquee loops, per the
[visual system](../brand/visual-system.md).

**Alternatives considered.**

- *Screen-recorder auto-zoom tools* ([OpenScreen](https://github.com/getopenscreen/openscreen)
  and [OpenVid](https://github.com/CristianOlivera1/openvid) are in our own catalog)
  suit the capture and zoom step. They give no scripted overlays or code reveals.
  Worth a trial for the raw capture, and a possible dogfood credit.
- *Pure three.js or WebGL scenes* give the most freedom and the most work. The
  content here is 2D windows and text, so the cost does not pay back.
- *Hand-edited timeline* (any NLE) is quick for one cut and slow for the re-shoots
  these dependencies guarantee (PR 2 to 5 change the footage).

**Licence check before starting.** Remotion's licence is "see LICENSE.md", and company
use can need a paid licence. Check it against the owner's and JumperMCP's status.

**Rendering.** Render on the M5. On `alder`, Remotion's downloaded headless Chrome
likely fails like Playwright's does on NixOS; pass `--browser-executable` with the
system Chrome (`CHROMIUM_PATH`) if rendering there. Verify when setting up.

## Repository layout

A self-contained `launch-video/` directory with its own `package.json`, outside the
site build, so it cannot affect the [size budget](2026-10-22_Performance-tuning.md).
It holds compositions, the capture-log schema, fixtures for the drawn lists (pinned
revision and licence) and a `render` script. Raw captures and rendered video stay out
of git; publish through a release asset or the chosen host, and record the exact
source revisions of the site, WebMCPlet and the drawn list in the video's description.

## Delivery

| Step | Deliverable | Acceptance | After |
| --- | --- | --- | --- |
| 1 | Remotion project, brand fonts and tokens, code-reveal and value-check components, run against a mock log | A 10 s test render matches the white/Prussian system | Now |
| 2 | Time a real ChatGPT run; pick the pool; screen it against the four rules | Duration recorded; screening table committed | PR 2 |
| 3 | V1 shoot and cut | The owner reviews; every on-screen value matches the catalog on the shoot date | PR 5 |
| 4 | V2 shoot and cut | The owner reviews; the drawn list's licence, revision and label are on screen | PR 4 and PR 6 packaging |
| 5 | V3 shoot and cut | The owner reviews; stock profile verified; requirements card matches the Chrome docs on the shoot date | PR 3 passed and PR 5 |
| 6 | Publish | The owner decides placement, the maintainer courtesy note, and the Chrome 162 token timing | Review passed |

Publication, other lists' maintainers and any third-party branding are the owner's
call, per the WebMCPlet PRD's scope.

## Open questions for the owner

1. V2 with a local agent (recommended), or a public CC0 mirror so ChatGPT can drive it?
2. Notify the drawn list's maintainer before publication?
3. Is a muted, captioned format acceptable for all three videos, or is a voice-over wanted
   later (this would reopen TODO 261014's voice question)?
4. Remotion licence status for the project.
5. Release order: V1 first, with V3 as the finale once PR 3 passes, or hold all three
   for one launch?

Contribution by Claude Code (AI)
