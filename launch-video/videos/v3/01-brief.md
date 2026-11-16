# V3: no agent

**Article claim:** "Chrome offers users an in-browser LLM that does the same job on
beefier machines." V3 premieres under "Example 3: Everything in-browser"; the
article's "Prompt AI" reads "Prompt API".

**Shows:** a visitor on Chrome with an empty data folder opens Awesome Open\*,
searches without any download, downloads Chrome's on-device model from the panel,
and asks the assistant in the page.

- **Question (owner, 2026-11-16):** "Find me two video editors that run in the
  browser and compare them." V1's "self-hosted" question returns only OpenCut here:
  the catalog records self-hosting in text for OpenCut alone and no video editor has
  the run mode "Self-hosted server"; ChatGPT found OpenReel's hosting on the web,
  which the in-browser model cannot do.
- **Browser:** Chrome 157 started with `--user-data-dir` (an empty folder) and
  `--no-first-run`; no feature flags (shown on `chrome://flags`), extension,
  account or key. WebMCP stays off; the panel does not need it. The visitor clicks
  by hand; nothing drives the browser.
- **Before the shoot:** PR #348 (download bar in the panel's accent colour) merged
  and deployed; check that the live page serves WebMCPlet 0.2.2.
- **Value check:** the answer's rows against the catalog of the shoot date; the
  model's prose labelled generated, as the panel already labels it ("AI response").
- **End card:** the Prompt API's requirements as Chrome documents them on the shoot
  date (desktop Chrome 148 or later, 22 GB free, more than 4 GB VRAM or 16 GB RAM
  and 4 cores).
- **Length:** 45 to 60 s; the download is sped up and tagged.

## Trial (2026-11-16, 3:38 AM, 11:10, not for the cut)

Owner's run with V1's question on the live site, WebMCPlet 0.2.1: flags page, site,
search "video editor", download, then the question. Answers held no result or
OpenCut alone; the download bar showed the browser's default blue.

## Rehearsal (2026-11-16, not footage)

Six runs of the browser question on a clone of the trial profile (model on disk),
driven through the DevTools protocol:

| Run | Rows returned | AI response |
| --- | --- | --- |
| 1 | OpenReel Video, OpenFilm, OpenVid, openMarquee | its plan ("I need to arrange the items first…"), no comparison |
| 2 | OpenReel Video, OpenFilm, OpenVid | three with descriptions and links |
| 3 | OpenReel Video, OpenFilm, OpenVid | "Here are two…", then three with descriptions |
| 4 | OpenReel Video, OpenFilm, OpenVid | three names and links only |
| 5 | OpenReel Video, OpenFilm | two with descriptions |
| 6 | OpenReel Video, OpenFilm, OpenVid | three, then "I have compared them using the cabinet_compare tool" |

Every run returned at least two rows, in 4 to 8 s. The prose often lists three
and seldom compares values; the rows and the Cabinet link carry the comparison.
