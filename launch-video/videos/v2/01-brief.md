# V2: on any list

**Article claim:** "We'll make our solution a drop-in tool for any Awesome List. To
test this right away, we'll inject the tool in a random list." V2 premieres under
that paragraph; the article's "using ChatGPT browser again" changes to the agent
below.

**Shows:** a list drawn on screen from the screened pool gets WebMCPlet with one
command, GitHub stars included, and a coding agent asks the same kind of question
as V1 through the page's tools.

- **Draw:** from the lists that pass `00-screening.md` (4 of 6 on 2026-11-16:
  open-source-mac-os-apps, awesome-python, awesome-go, awesome-nix).
  `node scripts/draw.mjs v2 <shoot date>` fixes the pick: the seed is SHA-256 of
  `00-screening.json` and the date, shown on screen. Screening is committed before
  the shoot, so anyone can repeat the draw.
- **Question:** "Use the page's tools to find me {ask} and compare them.", with
  `ask` from the drawn list's own section (for example "two Go video libraries").
  Caption: same kind of question, another list.
- **Command:** `node build.cjs try https://github.com/<list> --github-stars on`,
  from the release that carries `github.js` (PR #347), with a clock from the first
  command to the first tool call.
- **Client:** Claude Code in a terminal, driving Chrome (started with
  `--enable-blink-features=WebMCP`) through `chrome-devtools-mcp` 1.12.0 with
  `--categoryExperimentalWebmcp=true --no-usage-statistics --no-performance-crux`.
  Terminal and browser share the screen; each is a box on the stage.
- **On screen throughout:** "Local preview. No affiliation with this list", the
  list's name, maintainer, licence and revision. awesome-python is CC BY 4.0, so
  its credit line is required if it is drawn.
- **Values:** stars as fetched by the build step, with their request time; the
  list's own fields otherwise read Unknown.
- **Capture:** SDR screen recording on the M5, regions marked as in V1; window
  bounds can come from the DevTools protocol.
- **Length:** 45 to 60 s. Same video layer and stage as V1 ([B-PR343-01](../../../brand/decisions/B-PR343-01.md)).

**Before the shoot:** PR #347 merged or its branch checked out; re-run screening on
the shoot date if a list changed; draw on the shoot date.
