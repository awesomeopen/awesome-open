# Prompt API model test on the M5

PR 3 of the [WebMCPlet PRD](../../PRD/2026-11-04_WebMCP-for-Awesome-lists.md#delivery):
a throwaway test of Chrome's on-device model driving the page tools through the PRD's
three journeys. This directory stays on its branch; it is not merged.

**Result:** with short item refs and a recovery message that names the next tool,
the model passed 56 of 60 runs and 155 of 175 actions were valid. With the page's
tools passed through unchanged, it passed 25 of 60. The context window is 9,216
tokens and a run peaked at 5,607.

## Setup

| | |
| --- | --- |
| Machine | M5 Max, 18 cores, 128 GB, macOS |
| Browser | Google Chrome 156.0.8078.80, own profile, `--enable-blink-features=WebMCP` |
| Model | Optimization Guide On Device Model 2025.8.8.1141, base `v3Nano` 2025.06.30.1229, 4.0 GB; downloaded on 2026-11-09 in 2 minutes after a click |
| Awesome Open | Built from `main` `7a199b2`; catalog `data-source-sha` `9b6d1e4` |
| Mac list | [open-source-mac-os-apps](https://github.com/serhii-londar/open-source-mac-os-apps) `applications.json` at `23b6184`, 988 apps, 984 items by normalized repository URL |
| Runs | 20 per journey per configuration, run on 2026-11-09; at most 8 turns and 30 s per turn |

`controller.js` gives the model the page's tool list and asks for one JSON action per
turn. `responseConstraint` limits each turn to a call of a registered tool with that
tool's argument schema, or a final answer with `text` and `ids`. The controller
dispatches calls through `document.modelContext.executeTool` and returns each result
as the next prompt. `maclist/` registers `list_find` and `list_get`, which are shaped
like `cabinet_find` and use `site/search.js`.

## Journeys and checks

| Journey | List | A run passes when |
| --- | --- | --- |
| "Find a video editor and compare two." | Awesome Open | The last `cabinet_arrange` selects exactly two of the 13 projects that `cabinet_find` returns for "video edit", a later `cabinet_compare` succeeds, and the answer meets the general rules |
| "Find a Markdown editor." | Mac list | `list_find` succeeds, and the answer's `ids` include one of the 13 items `list_find` returns for "markdown edit" |
| "Manage family photos on my own server." | Awesome Open | `cabinet_find` succeeds, `ids` is empty and the text names no catalog project |

General rules for every answer: each ID in `ids` came from a tool result in that run,
and the text names no item the tools did not return. Names are matched as whole,
case-sensitive words of four or more characters, outside URLs.

An action is valid when it parses, names a registered tool and that tool returns
`ok: true`, or when it is an answer that meets the general rules.

## Results

| Configuration | Video compare | Markdown editor | Family photos | Valid actions |
| --- | --- | --- | --- | --- |
| A: tools unchanged | 0/20 | 5/20 | 20/20 | 99/127 |
| B: short refs | 0/20 | 18/20 | 20/20 | 118/139 |
| C: short refs, `empty_selection` names `cabinet_arrange` | 17/20 | 19/20 | 20/20 | 155/175 |

- **B: short refs.** The controller replaces each item ID with `r1`, `r2`, … in what
  the model reads, and maps refs back before a tool call or in `ids`. Unknown refs
  pass through, so the tool rejects them.
- **C: recovery message.** The model reads `empty_selection` as "Nothing is selected.
  Call cabinet_arrange with ids from cabinet_find and its revision, then call
  cabinet_compare." in place of "Select at least one project first."; the page's
  tool is unchanged.

Failures by cause:

| Cause | A | B | C |
| --- | --- | --- | --- |
| Called `cabinet_compare` before `cabinet_arrange`, then answered on `empty_selection` | 14 | 20 | 0 |
| An ID in `ids` was not in any tool result | 12 | 1 | 0 |
| `UnknownError: kErrorUnknown` from `prompt()`, right after a 12-result tool reply | 6 | 0 | 3 |
| Turn exceeded 30 s, generating past a complete action | 3 | 1 | 0 |
| Selected three or six projects when asked to compare two | 0 | 0 | 1 |

### Speed and context, configuration C

| Journey | Median run | Median turn | Slowest 10% of turns from | Peak context use |
| --- | --- | --- | --- | --- |
| Video compare | 4.3 s | 0.7 s | 1.4 s | 5,607 / 9,216 |
| Markdown editor | 3.3 s | 0.8 s | 3.2 s | 1,726 / 9,216 |
| Family photos | 1.3 s | 0.6 s | 0.6 s | 1,526 / 9,216 |

Context use is `session.contextUsage` after each turn. The instructions and tool list
take 558 tokens on Awesome Open and 410 on the Mac list. Session creation takes a
median 0.26 s once the model is on disk.

### Answer text

The deterministic checks read `ids`, not the prose. A manual read of configuration C:

- **Refs in prose.** All 19 Markdown answers wrote refs into the text, and 14 labelled
  an item with another item's ref, after skipping Markup (`r9`). `ids` remained correct.
  One answer wrote "Edmunds" for Edmund.
- **Reviewed alternatives.** 3 of 17 passing video answers said OpenCut "has an
  alternative called CapCut"; the record lists CapCut as the product OpenCut is an
  alternative to.
- **Evidence.** 1 of 17 passing video answers stated stars and licenses from the
  comparison. The others restated descriptions.
- **No match.** Every family-photo run searched the full or nearly full phrase, got
  `total: 0` and answered "This list has no match" without a shorter query, so no
  run met the image editor OpenPhoto or the food diary openplate.

### Chrome behavior found

- `responseConstraint` rejects a schema containing `uniqueItems` with
  `NotSupportedError`; `pattern`, `maxItems`, `minimum`, `maxLength`, `anyOf` and an
  empty `properties` object work. The controller strips `uniqueItems`, and
  `cabinet_arrange` still rejects duplicates.
- `LanguageModel.availability()` reported `downloadable` in a fresh headed profile.
  `create()` from a click downloaded the model; Playwright's own launch flags
  disable the component updates the download uses, so `run.cjs` starts Chrome itself.
- `session.contextWindow` is 9,216 tokens.

## Run it

```sh
python3 scripts/build_site.py --output <site> --source-sha "$(git rev-parse HEAD)" --production
# <maclist> holds applications.json and categories.json from the pinned commit, and sha.txt
node experiments/prompt-api-m5/run.cjs --site <site> --maclist <maclist> --profile <chrome-profile> \
  --runs 20 --turn-ms 30000 --refs on --messages arrange --out <results.json>
```

The profile must hold the model; the first `create()` in it needs a click. Each run
opens a fresh page and session. `results/` holds every report, including each
turn's prompt, raw output, latency and context use.

## Follow-up, 2026-11-10

The shipped assistant in `webmcplet/webmcplet.js` runs through the panel with
`scripts/check_webmcplet_assistant.cjs`, on a catalog that had grown from 569 to 579
projects. Results, 20 runs each:

| Report | Video compare | Markdown editor | Family photos |
| --- | --- | --- | --- |
| `d-webmcplet-assistant.json`: shipped assistant, current catalog | 8/20 | 20/20 | 20/20 |
| `e-config-c-rerun-original-catalog.json`: configuration C, original build | 17/20 | 17/20 | 20/20 |
| `f-config-c-current-catalog.json`: configuration C, current catalog, Cabinet tools only | 2/20 | not run | not run |

Configuration C reproduces its result on the original build and drops to 2/20 on the
current catalog, where "video editor" returns 12 projects. The model then selects three
to six projects when asked to compare two. All 12 failures of the shipped assistant
selected three. Two controller details changed results: tools listed in name order, as
Chrome's `getTools()` returns them (in registration order, 0 of 5 recovered from
`empty_selection`), and `list_find` offered without its optional `section` argument, which
the model otherwise filled with invented section names.
