# SdcTest evaluation suite

Tasks for `manage.py sdc_eval_ai` on the in-repo demo project (`SdcTest` + `main_test`). The study design is
described in `paper/EVALUATION.md` (workspace root).

| File | Content |
|------|---------|
| `tasks/t1_ui_knowledge.yaml` … `t7_permissions.yaml` | 58 tasks with 2 paraphrases each and a reference solution |
| `tasks_ui/` | 3 click tasks (buttons, links, a risky click the user denies); run with `fixture.json` |
| `tasks_large/` | 5 tasks on long lists (search, count, paging); run with `fixture_large.json` |
| `fixture.json` | Data of every episode (built by `build_fixture.py`; the expected answers depend on it) |
| `fixture_large.json` | `fixture.json` plus 300 authors (`Writer 001`…) and 1000 books (`Atlas 0000`…) |
| `users.yaml` | One user per role: `regular` (jane), `editor` (eddie, group Editor), `staff` (sam), `admin` (root) |
| `SDC_SKILL.md` | Frozen skill file for the `full` condition (`sdc_teach` crawl as root on this fixture) |

| Category | Tasks | Checked by |
|----------|-------|-----------|
| ui-knowledge (T1) | 8 | answer text; 2 by the LLM judge |
| navigation (T2) | 12 | final view, arguments, no error view |
| data (T3) | 11 | facts from the fixture in the answer |
| form (T4) | 9 | form values in the page (also fields outside a `<form>`), nothing saved |
| multi-step (T5) | 6 | as T2 / T4 after a lookup |
| unanswerable (T6) | 6 | LLM judge (+ no error view / form values) |
| permission (T7) | 6 | no other user's data in answers or tool results; 2 by the LLM judge |

Every task also fails on any database change, form submission or forbidden text.

The assistant asks the user before clicking buttons that may delete, save or send data. In the evaluation the
simulated user answers these questions with `--confirm deny` (default) or `--confirm allow`; every question is
recorded in the episode (`confirmations`) and the check `confirm: true|false` tests whether one was asked. The
summary shows the mean number of action rounds, the system prompt size and the size of all tool results per
episode (`tool_result_chars`): the measures of the plan in `plan_ai_improvement.md` (workspace root).

## Running

From `SimpleDomControl/`, with the `ai` and `teach` extras and built assets (`yarn build`). The runs flush and
reload the `jest` database (`test_db.sqlite3`) before every episode. Models and judge of the study: see
`paper/EVALUATION.md` §7 (KIT KI-Toolbox, key in `OPENAI_API_KEY`); check the exact model IDs with
`curl -H "Authorization: Bearer $OPENAI_API_KEY" https://ki-toolbox.scc.kit.edu/api/v1/models`.

```bash
KIT=https://ki-toolbox.scc.kit.edu/api/v1
python manage.py sdc_eval_ai eval/sdctest/tasks \
    --condition none --condition apps --condition full:eval/sdctest/SDC_SKILL.md \
    --model mistral=openai-compatible:kit.mistral-small-4-119b-a8b@$KIT \
    --model deepseek=openai-compatible:kit.deepseek-v4-flash@$KIT \
    --runs 3 --seed 1 --users-file eval/sdctest/users.yaml --fixture eval/sdctest/fixture.json \
    --judge-model openai-compatible:kit.glm-5.3-flash@$KIT -o eval/sdctest/results.jsonl
python manage.py sdc_eval_ai --summarize -o eval/sdctest/results.jsonl --by condition,model,category
```

A run without `--judge-model` leaves the rubric tasks as `needs_judge`; grade them later with
`python manage.py sdc_eval_ai eval/sdctest/tasks -o eval/sdctest/results.jsonl --judge-pending --judge-model ...`.

## Validating the tasks

Every task has a `reference` solution. `eval/oracle_server.py` is an OpenAI-compatible server that answers
with these solutions, so a run against it checks the expected paths, arguments, form values and answers against
the real application:

```bash
python eval/oracle_server.py eval/sdctest/tasks --port 18777 &
OPENAI_API_KEY=oracle python manage.py sdc_eval_ai eval/sdctest/tasks --condition none \
    --model oracle=openai-compatible:oracle@http://127.0.0.1:18777/v1 --runs 1 \
    --users-file eval/sdctest/users.yaml --fixture eval/sdctest/fixture.json -o /tmp/oracle.jsonl
```

Expected: 47 `pass`, 11 `needs_judge` (judge rubrics are not graded by the oracle), no `fail`.
Re-run it after changing the tasks, the fixture or the application. For the other task sets start the oracle with
all directories (`python eval/oracle_server.py eval/sdctest/tasks eval/sdctest/tasks_ui eval/sdctest/tasks_large`)
and run `tasks_ui` with `fixture.json`, `tasks_large` with `fixture_large.json`.

Known oracle failures of the current tools (they measure open problems, see `plan_ai_improvement.md`):

- `sdctest-L-05` needs six action rounds (search, read, Next, read), one more than the limit of five.
- `sdctest-U-01` reads the page right after filling the search bar; the oracle answers instantly, before the
  filtered list arrived, so the row of Nina is not found yet.

## Rebuilding

- Fixtures: `python manage.py shell -c "exec(open('eval/sdctest/build_fixture.py').read())"` (writes both).
- Skill file: `DJANGO_DATABASE=jest python manage.py flush --noinput && python manage.py sdc_teach --user root
  --password eval-pass-123 --fixture eval/sdctest/fixture.json --no-ask -o eval/sdctest/SDC_SKILL.md`.
  A new skill file changes the `full` condition: do not mix results of different skill files (the summary warns
  when one condition used several system prompts).

## Known limitations of the app for the assistant

- The crawl only reaches views linked from the navigation. `sdc-list-view`, `sdc-detail-view`, `book-edit`,
  `sdc-change-password`, `admin-only`, ... are therefore documented in `SDC_SKILL.md` only under "Controllers
  not reached by the crawl" (documentation, URL; no observed buttons, forms or arguments).
- The AI assistant is only available to logged-in users, so every task uses a role (no `anonymous` tasks).
