# Fewer tokens for AI agents working with SDC — plan

Goal: an AI agent (Claude Code, Codex, Cursor, …) that develops or operates an SDC project needs clearly fewer tokens
and turns for typical tasks, without losing correctness. Three levers:

1. **Scripts**: deterministic, non-interactive commands do multi-file work and answer tersely, so the agent does not
   read and edit five files by hand or parse 6k tokens of JSON.
2. **Easy-to-find skills**: small, focused instructions that the agent loads only when the task needs them
   (progressive disclosure), shipped with the framework version they describe.
3. **Measurement**: a fixed benchmark shows the effect; no change is kept that does not pay off.

Two audiences:

- **A — coding agents** that build an SDC project (main target of this plan).
- **B — runtime agents** that use a running app (the AI assistant `<sdc-ai-assistant>`, MCP clients). Already lean
  (index mode + `describe`); only small follow-ups (M4).

## Current state (measured 2026-11-11)

| What an agent has today | Cost |
|---|---|
| Generated project: no `AGENTS.md`, `CLAUDE.md` or skills | the agent explores framework source in site-packages |
| `DOCUMENTATION.md` (workspace root, not shipped with the package) | ~11 400 tokens, all or nothing |
| `manage.py sdc_get_controller_infos` (test project) | ~6 000 tokens of indented JSON with absolute paths |
| `sdc_cc`, `sdc_new_model`, `sdc_init`, `sdc_teach` | call `input()` when an argument is missing: agents hang or retry |
| `yarn sdc_test` / `yarn build` | long logs (console output of every controller) the agent has to read |
| `SDC_SKILL.md` / `.assistant.md` / `.data.json` of an app (runtime knowledge) | 5–9k tokens; index mode already avoids sending all of it |
| MCP `initialize` instructions | contain the whole skill index (grows with the app) |

Typical expensive moments seen in practice: finding which files make up a controller pair, wiring a new model
(model, forms, JS model, URLs, organizer), framework pitfalls found only by debugging (e.g. arrow functions as
`this.events` handlers get the wrong `this`), and reading build/test logs.

## Principles

- **Always loaded ≤ ~800 tokens**: the project `AGENTS.md` only says what the project is, the 5–10 commands, the
  hard rules, and which skills exist. Everything else is loaded on demand.
- **Skills are short and task-shaped**: `SKILL.md` ≤ ~80 lines with a precise `description` (that is what the agent
  matches on), details in `references/*.md` read only when needed, scripts for the mechanical parts.
- **Scripts answer in a few lines**: relative paths, one line per item, `--json` only when asked, errors with the
  exact next step. Never prompt; fail with a message instead.
- **Generated, versioned, checked**: skills and `AGENTS.md` come from templates of the installed SDC version, are
  updated by a command, and tests check that every command and path they mention exists.

## Decisions to make before M1 (owner: maintainer)

| # | Question | Proposal |
|---|---|---|
| D1 | Where do skills live in a project? | `.claude/skills/sdc-*/SKILL.md` (Claude Code format; plain Markdown that other agents can read too) plus `AGENTS.md` as the tool-neutral entry point; `CLAUDE.md` contains only `@AGENTS.md` |
| D2 | Command naming | One command with sub-commands: `manage.py sdc_agent overview|where|check|new-controller|new-model|test|build` |
| D3 | Installed by default? | Yes: `sdc_init` writes the kit; `sdc_agent kit --update` refreshes it after an SDC upgrade; projects can opt out (`--no-agent-kit`) |
| D4 | Project-specific content in `AGENTS.md` | A generated block (apps, models, commands) between markers, the rest hand-editable and kept on update |
| D5 | Benchmark agent | Claude Code headless (`claude -p --output-format json`, reports tokens and turns); same model and tasks for every run |

---

## M0 — Baseline benchmark — **done**

Status (2026-11-11): decisions D1–D5 accepted as proposed. Harness in `scripts/agent_bench/` (`bench.py`
`selftest|seed|run|summarize`, `project.py`, `tasks.py`, `agent.py`, `run_check.py`), design in
[agents.architecture.md](agents.architecture.md). Six tasks (`controller_list`, `model_review`, `server_call`,
`fix_counter`, `mcp_token`, `document`); `selftest` passes: every check fails on the seeded project and passes with
the reference solution. Baseline (WP0.3, run by the maintainer): 17/18 passed (the failure was most likely a
valid fix the check did not accept; check corrected), 10.4M input tokens, 7.65 USD for 18 runs; report with
findings in [agents-bench/2026-11-11-baseline.md](agents-bench/2026-11-11-baseline.md). Differences from the text below: no Jest task (checks need no Node
build); the agent runs with an allow-list of tools by default (`--permissions restricted`).

Exit criterion: tokens, turns, time and success of every task are recorded for a fresh project without the kit.

### WP0.1 — Tasks
6–8 tasks typical for SDC work, each with an automatic check (pytest/Jest or file assertions), e.g.:
1. Add a controller `book-list` to an app that lists `Book` records (pair + organizer + URL).
2. Add a model `Review` (FK to `Book`, rating 1–5) with create/edit forms and make it editable in the UI.
3. Add a server call to a controller and call it from a button.
4. Fix a planted bug (handler with wrong `this`, missing organizer import, wrong `contentUrl`).
5. Expose a model read-only over MCP and create a token for it.
6. Write a Jest test for a controller.

### WP0.2 — Harness (`scripts/agent_bench.py`)
Creates a fresh project per run (like `pytests/conftest.py`), optionally installs the kit, runs the agent headless
per task, records usage from the JSON output, runs the check, writes JSON lines. Reuses ideas of `sdc_eval_ai`
(runs, summaries) but is a dev script, not a shipped command. ≥ 3 runs per task and condition.

### WP0.3 — Baseline run and report
Numbers per task: median input/output tokens, turns, success. Stored in `paper/` or `docs/` for later comparison.

---

## M1 — Agent-friendly scripts (`manage.py sdc_agent`) — **done**

Status (2026-11-11): WP1.0–WP1.6 implemented. Library `sdc_core/agent/` (`project_map.py` on top of the
`sdc_teach` discovery, `checks.py`, `runner.py`), command `manage.py sdc_agent overview|where|check|new-controller|
new-model|test|build`, no prompts outside a terminal in `sdc_cc`, `sdc_new_model`, `sdc_init`
(`utils.can_prompt` / `missing_argument`), env files in `sdc_core/apps.py::update_sdc_env_files`; tests in
`pytests/test_sdc_agent.py`. Differences from the text below:
- No `--no-input` flag: "not a terminal" is the switch (agents and scripts never have one).
- JS controllers without server view are listed as *client-only* (mixins such as `sdc_auto_submit`); `check` only
  reports them when their `contentUrl` has no view.
- `new-controller` / `new-model` call `sdc_cc` / `sdc_new_model` only; `sdc_make_model_js` and `sdc_update_url`
  are not needed for a new model (the generator links the templates).
- The arrow-function check looks at the body of every arrow function in event registrations of the constructor;
  arrow functions registered in `willShow` are fine (verified against the client lifecycle).

Exit criterion: every M0 task can be done with the scripts without reading framework source; all commands are
non-interactive; outputs are ≤ ~40 lines for the test project.

### WP1.0 — No changes to tracked files when `manage.py` runs (from the baseline)
`SdcCoreConfig.ready()` rewrites `Assets/.sdc_env` and `Assets/.sdc_python_env` on every start in DEBUG; write
them only when their content would change. Agents saw the diff and spent turns reverting it.

### WP1.1 — Never prompt
`sdc_cc`, `sdc_new_model`, `sdc_init`, `sdc_teach`: when stdin is not a terminal (or with `--no-input`), missing
arguments raise `CommandError` with the exact flags to pass, instead of `input()`. Tests per command.

### WP1.2 — `sdc_agent overview`
Compact project map, one line per item, relative paths:
```
app main_test
  controller book-edit   main_test/Assets/src/main_test/controller/book_edit/  view sdc_views.py:51  /sdc_view/main_test/book_edit
  model Book(title, author→Author)  forms: edit, create, test  sync: yes  mcp: yes
```
Options: `--app`, `--json`. Replaces the need to read `sdc_get_controller_infos` (which stays for tools).

### WP1.3 — `sdc_agent where <tag|Model>`
All files of one controller pair or model (view class + line, template, JS, SCSS, organizer line, URL, tests,
JS model), so an edit needs no search.

### WP1.4 — `sdc_agent check`
Consistency check with one line per problem and the fix: JS without view, view without URL, controller missing in
the organizer, template without JS, model without forms used by the UI, undocumented models/controllers
(`sdc_prepare_teaching`), handlers defined as arrow functions in `this.events`, outdated bundles of bundled apps.
Exit code ≠ 0 on problems (usable in CI and by agents after an edit).

### WP1.5 — `sdc_agent new-controller` / `new-model`
Non-interactive wrappers of `sdc_cc` / `sdc_new_model` (+ `sdc_make_model_js`, `sdc_update_url`) that do the whole
wiring and print only the created/changed files and the next step.

### WP1.6 — `sdc_agent test` / `build`
Run `pytest`, `yarn sdc_test` or the asset build and print only a summary: passed/failed counts, failing test names
with the first relevant lines of each error, build errors. Full log written to a file whose path is printed.

---

## M2 — Agent kit: `AGENTS.md` and skills in every project — **done**

Status (2026-11-11): templates in `sdc_core/template_files/agent_kit/` (`AGENTS.md` ≈ 780 tokens, `CLAUDE.md`,
five skills, one reference file), installer `sdc_core/agent/kit.py`, `manage.py sdc_agent kit install|update|check`,
`sdc_init` installs the kit (`--no-agent-kit`), `sdc_agent check` warns about an outdated kit; tests in
`pytests/test_agent_kit.py` (incl. every `manage.py` line of the kit parsed by the real parsers) and
`pytests/test_sdc_agent.py`. Benchmark: baseline projects use `sdc_init --no-agent-kit`, the `kit` condition
installs the kit after seeding. Differences from the text below:
- WP2.4: no extraction from the Sphinx docs. The kit texts are written for agents (shorter, task-shaped) and
  checked by tests instead (commands parse, referenced files exist, sizes). While writing them, two errors in the
  root `DOCUMENTATION.md` were found and fixed: event handlers shown as arrow functions `(self, $el, e) => …`, and
  server calls described as `call_<name>` methods (the method is called by its exact name).
- WP2.5 (skills for developing SDC itself) is postponed until M3 shows the effect of the project kit.
- Outdated detection compares template hashes (the manifest stores the hash of the template each file came
  from), not version numbers: the install metadata of editable installs is unreliable.
- `sdc_agent` skips Django's system checks (their warnings preceded every answer).

Exit criterion: `sdc_init` creates the kit; `sdc_agent kit --update` refreshes it without losing edits; a test
verifies every command, flag and path the kit mentions.

### WP2.1 — Project `AGENTS.md` (+ `CLAUDE.md` → `@AGENTS.md`)
≤ ~800 tokens: what SDC is in 3 lines, the controller-pair rule, the commands (`sdc_agent …`, build, test), hard
rules (don't hand-edit the organizer, rebuild after JS changes, run `sdc_agent check`), list of skills with one line
each, and a generated block with the project's apps and models.

### WP2.2 — Skills (`.claude/skills/`)
| Skill | Loaded when the task is about | Contents |
|---|---|---|
| `sdc-controller` | views, controllers, templates, server calls | pair anatomy, lifecycle, `this.events` / `sdc_click`, server calls, `refresh`/`reload`, pitfalls; refs: lifecycle, events, navigation |
| `sdc-model` | data models, forms, sync, querysets | `SdcModel`/`SdcMeta`, permissions, forms, client `SdcQuerySet`; refs: model API, search forms |
| `sdc-api-mcp` | REST API, tokens, MCP | tokens & privileges, endpoints, MCP setup and tools |
| `sdc-testing` | tests, debugging | pytest/Jest setup (port 8765, `jest` DB), `sdc_agent test`, common failures |
| `sdc-ai-knowledge` | `sdc_teach`, docstrings, assistant | how to document so the assistant/MCP understand the app |

Each `SKILL.md` has a `description` that names the trigger words (controller, view, template, model, form, …) so
the agent picks it without reading others.

### WP2.3 — `sdc_agent kit install|update|check`
Writes/updates the kit from `sdc_core/template_files/agent_kit/` with a version stamp; keeps hand-written parts of
`AGENTS.md`; `check` reports an outdated kit (also part of `sdc_agent check`).

### WP2.4 — Reference slices instead of one big document
The skills' `references/*.md` are the relevant parts of the docs, each ≤ ~1 500 tokens. Source of truth stays the
Sphinx docs; a script extracts/updates the slices so they do not drift. Include the pitfalls found in practice (e.g.
the arrow-function `this` in `this.events`).

### WP2.5 — Repo-level skills for framework development
Same pattern for this workspace (SimpleDomControl + Client): skills for "release", "rebuild bundled apps and
snapshots", "add a REST/MCP feature", so agents working on SDC itself also stop re-reading `AGENTS.md`/docs.

---

## M3 — Measure and tune — **done**

Status (2026-11-11): kit run by the maintainer: 18/18 passed, input tokens −63 % (10.38M → 3.83M), turns −56 %,
cost −50 % (7.65 → 3.81 USD) against the baseline; every task cheaper. A second baseline with the new commands but
without the kit gained only −15 %: the kit (AGENTS.md naming the commands) is what makes agents use them. Report:
[agents-bench/2026-11-11-kit.md](agents-bench/2026-11-11-kit.md). Tuning (WP3.2): `bench.py run --transcripts` and
`bench.py analyze`; one round with 12 runs found a bug in `sdc_new_model` (missing imports), JS tests attempted
without `node_modules` and unrequested tests caused by the wording of `AGENTS.md`; all three fixed (same report).

Exit criterion: the M0 benchmark with the kit shows the gain per task; changes without effect are removed.

### WP3.1 — Benchmark with kit
Same tasks, model and runs as M0. Target (to confirm with the baseline): ≥ 30 % fewer input tokens and fewer turns
at equal or better success.

### WP3.2 — Tune
Look at transcripts: which files are still read, which skills are not found (description), which outputs are long.
Shorten or split; re-run.

---

## M4 — Runtime agents (assistant and MCP), smaller follow-ups — **WP4.1, WP4.2 done; WP4.3 open**

Status (2026-11-11): `SDC_MCP['instructions']` (`models` default, `index`, `none`) — the default keeps only the
exposed models of the index (test project: 6 528 → 1 289 characters per MCP session); `describe` refuses hidden
models. Field selection in `model_actions` (`fields`), MCP `model_load` / `model_get` (`fields`) and REST
(`?_fields=`), documented in OpenAPI. Tests in `pytests/test_mcp.py`, `pytests/test_rest_api.py`. WP4.3 needs paid
`sdc_eval_ai` runs (maintainer). Difference: no character cap; the cut is by content (models only).

### WP4.1 — MCP instructions
Put at most N lines of the index into `initialize` (e.g. models and top-level views); the rest through `describe`
and the resources. Setting `SDC_MCP['instructions']` = `index` | `short` | `none`.

### WP4.2 — `model_load` field selection
Optional `fields` argument (subset of exposed fields) so large records do not fill the context; same for REST
(`?_fields=`).

### WP4.3 — Measure the assistant
Use `sdc_eval_ai` (already records tokens) to compare `SDC_AI_SKILL_MODE` `full` vs `index` on the existing tasks
and make the cheaper one the default if success holds.

---

## M6 — Comparison with other stacks (condition `free`) — **first run done (10 of 18 runs)**

Added 2026-11-11 on request: the same six tasks where the agent may use any framework except SDC, starting from a
plain Django seed of the same app, with framework-neutral equivalents of the SDC-specific tasks (decisions of the
maintainer). Design: [agents.architecture.md](agents.architecture.md), "Condition `free`". `selftest --condition
free` passes. First run (10 of 18 runs, all passed): SDC with the kit costs about the same as plain Django
(2.17 vs 2.04 USD on the same 10 task/runs), SDC without the kit twice as much; SDC is cheaper where the feature is
built in (MCP: 0.20 vs 0.36 USD), plain Django for simple pages. SDC runs carry ~21k tokens context per turn vs
~13k — hypothesis: verbose generated files. Report: [agents-bench/2026-11-12-free.md](agents-bench/2026-11-12-free.md).
Open: complete the run (with `--transcripts`) and check the context hypothesis.

## M5 — Docs and release — **done**

Status (2026-11-11): Sphinx page `docs/ai_agents.rst` (kit, skills, `sdc_agent`), `docs/core.rst` (`sdc_agent`, kit
files of `sdc_init`), root `DOCUMENTATION.md` and `AGENTS.md`, CHANGELOG; released as 0.164.0 (server and client in
lockstep; the client has no code change).
- Sphinx page "Working with AI coding agents" (kit, skills, `sdc_agent`), CHANGELOG, `AGENTS.md` of this workspace.
- Release in lockstep (server only; client unchanged unless M1 touches the build output).

## Dependencies

```
M0 ──► M3
M1 (WP1.1 first) ──► M2 (skills reference the scripts) ──► M3
M4 independent (after M0 for numbers)
M1 + M2 + M3 ──► M5
```

## Risks

| Risk | Mitigation |
|---|---|
| Skills drift from the code | generated from versioned templates; test checks every command/flag/path they mention; `kit check` |
| Skills are not found or loaded too often | precise trigger words in `description`; measured in M3 |
| The benchmark is noisy or expensive | few tasks, ≥ 3 runs, medians; run only for M0/M3, not in CI |
| Agent-tool lock-in | Markdown + `AGENTS.md` work for any agent; Claude Code format only for the folder layout |
| `sdc_agent` duplicates existing commands | wrappers call the existing commands; existing ones stay unchanged for scripts |
