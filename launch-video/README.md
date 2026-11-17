# Launch videos

Production pipeline for the WebMCPlet launch videos planned in
[the launch video PRD](../PRD/2026-11-15_WebMCPlet-launch-videos.md). Each video is
made in numbered stages. A stage reads the files of earlier stages and writes its
own, so any stage can be re-run alone and its output compared. Nothing a stage
generates is edited by hand.

Requires Node.js 18 or later and `ffmpeg` with `ffprobe` on the path. Run
`npm ci` once in this directory.

## Stages

| Stage | File in `videos/<id>/` | Command | Written by |
| --- | --- | --- | --- |
| 0 V2 only | `00-pool.json`, `00-screening.*`, `00-draw.json` | `node scripts/screen.mjs v2`, `node scripts/draw.mjs v2 <date>` | Script; the pool is written by hand |
| 1 Brief | `01-brief.md` | | Owner and Claude |
| 2 Beats | `02-beats.json` | | Owner and Claude |
| 3 Storyboard | `03-storyboard/` (stills, `contact.jpg`) | `npm run storyboard <id>` | Script. **Gate 1:** the owner reviews the contact sheet |
| 4 Capture | `04-capture/session.json`, `events.json`, the recording | | Recorded by hand; `session.json` names the file and its SHA-256 |
| 5 Facts | `05-facts.json` | `npm run facts <id>` | Script, on the shoot date |
| 6 Render | `06-render/` (`out.mp4`, `poster.png`, `captions.vtt`) | `npm run render <id>` | Script; runs `prepare` first |
| 7 QC | `07-qc.md`, `06-render/contact.jpg` | `npm run qc <id>` | Script. **Gate 2:** the owner reviews the render |

Gate decisions go in `videos/<id>/approvals.md`, append-only, naming the reviewed
files by SHA-256, so a re-run of QC never overwrites them. Each run appends a line to `videos/<id>/production.log`: time, stage, repository
revision and the hashes of its inputs. Recordings, stills and renders are
git-ignored; their hashes are in `session.json` and the log.

## What each file holds

- **`02-beats.json`:** size and frame rate; `segments`, the capture stretches in
  capture seconds with their playback speed; `beats`, each caption with its output
  time range; `overlays`: `clock`, `code` (a repository file, the text of its first
  line and a line count) and `valueCheck` (catalog projects and fields).
- **`boxes`** (in `02-beats.json`): the stage layout. Each box shows a named
  capture region with a label naming its source, from one output second to
  another, at keyframed positions `[centre x, centre y, width]`. A box with a
  `parent` lifts out of where its region sits in the parent and returns there.
  `kind: "site"` marks Awesome Open\* content. Without `boxes`, the older single
  camera (`keyframes` in `events.json`) frames the capture.
- **`04-capture/events.json`:** `regions`, named rectangles in capture pixels with
  keyframes in capture seconds. Marked by hand for footage from other clients
  (V1); logged through the DevTools protocol where the browser is ours (V2, V3).
- **Takes:** `session.json` may list several recordings under `takes`, each with
  `source`, `sha256` and `size`; a segment names its `take`, and region keyframes may
  name one. A switch of take is named on screen like a cut.
- **Segments** may carry `cutNote` (named for 2.5 s after a cut, with the left-out
  times). The speed tag and real-time clock in the top right mark sped-up stretches.
- **`intro` and `outro`** (in `02-beats.json`): an image from `images/` with a
  kicker, title and subtitle (`text: "dark"` for light images). The opening card
  shows for 2 s and is the poster, used as the YouTube still; the closing card
  shows for 2 s and fades to black over 1 s. The opening card carries the
  Awesome Open\* fruit (`mark: "webmcplet"`: the WebMCPlet lockup) and the Jumper
  MCP mouse in the top-right corner. Beat, box and overlay times count from the end of the
  opening card; `render` offsets the `.vtt` to match.
- **`highlight` overlays:** where to look, numbered 1 to 3 per video. A `box` and
  a `rect` in capture pixels follow that box as it moves; `at` is a rect in output
  pixels. `style` is `frame` or `underline`; `badge` moves the number's centre.
- **`masks`** (in `04-capture/events.json`): rectangles in capture pixels and
  capture seconds, filled with `maskColor`, that cover parts of the capture outside
  the demonstration (V2: the conversation before the recording started).

The video layer (captions, labels, clock, tags, claims) is neutral and separate
from the site's style; see [B-PR343-01](../brand/decisions/B-PR343-01.md).
- **`05-facts.json`:** each shown value with its label, source (`catalog`, `web` or
  `generated`) and observation date, plus the SHA-256 of the catalog it was read
  from. The overlay reads only this file. `null` renders as Unknown.

`scripts/prepare.mjs` gathers the render's inputs: brand tokens from
`site/design/tokens.css`, fonts from `site/vendor/`, capture segments cut from the
recording (checked against its SHA-256), and code read from repository files at
that moment. QC fails a render whose code has since changed in the repository.

## QC checks

Frame count and size, cards included; blank frames (fail, except the closing fade) and stills of 2 s or more (warning,
since screen captures hold still); caption reading speed of at most 17 characters
per second and at least 1.5 s on screen; every value-check field present in
`05-facts.json`; every code reveal matching its repository file.

## Layout

`src/` holds the Remotion composition (`Video.jsx`) and its components: `Camera`,
`Card`, `Caption`, `Clock`, `CodePanel`, `Highlight`, `Stage` and `ValueCheck`. `videos/test/` is a 10 s pipeline
check on V1 take 3. `public/` and `src/generated/` are written by `prepare` and
git-ignored.

Remotion is free for individuals and companies of up to three people
([licence](https://www.remotion.dev/license)).
