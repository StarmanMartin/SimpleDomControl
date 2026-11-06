# Changelog

Changes of the Python package `SimpleDomControl`. Changes of the JavaScript
runtime are listed in the
[sdc_client changelog](https://github.com/StarmanMartin/SimpleDomControlClient/blob/main/CHANGELOG.md).
The server and the client are released with the same version number.

## Unreleased

### Changed
- AI assistant: elements and forms of `read_page` have stable ids (`id` instead of a position `index`) that stay
  the same while the element is in the page, also when other parts re-render. `click` and `fill_form` take these
  ids; `click` accepts the element's `text` and refuses the click if the element changed; an id of a removed
  element is reported as gone. Protocol change: release server and client together.
- AI assistant: `read_page` returns an outline by default (visible text with `[#id label]` markers, no HTML) and
  summarises long lists and lists with a search bar (first 20 rows, total, search form, Next/Prev ids). New
  arguments `mode` (`outline`/`html`), `scope` (element, form or list id, or controller tag) and `rows`
  (`[from, to]`).
- AI assistant: `navigate`, `click` and `fill_form` return the outline of the page afterwards (`page`; setting
  `SDC_AI_PAGE_IN_RESULTS`, default `True`). `fill_form` on a view that updates on change waits until it accepts
  changes (sdc-update-on-change ignores them shortly after rendering) and until its update arrived; clicks wait
  for the page to settle. The action round limit is the setting `SDC_AI_MAX_ACTION_ROUNDS` (default 5).

### Added
- AI assistant: `SDC_AI_SKILL_MODE = 'index'` puts an index of the skill data (`SDC_AI_SKILL_DATA_FILE`, one line
  per view, controller and model, plus the recipes) into the system prompt instead of the whole skill file; the
  new server tool `describe` returns the full documentation of one item. `sdc_eval_ai` condition `index[:file]`.
- `sdc_teach --users-file roles.yaml`: crawls once per role; every view says which roles may open it. The crawl
  also opens the generic views of every SDC model (list, detail, create, edit; `--no-model-routes` skips them)
  and the skill file starts with *Common tasks*: generic recipes, the model routes with the roles that opened
  them, and the recipes of the new JSDoc tag `@ai-task`.
- `sdc_teach --audience agent|assistant|both` (default `both`): also writes `SDC_SKILL.assistant.md` for the AI
  assistant, without developer details (ready check, socket traffic, server views) and without controllers
  tagged `@ai-hidden`; the assistant prefers it (`SDC_AI_SKILL_FILE` default `None`). JSDoc tags `@ai-hidden` and
  `@ai-summary` of controller classes, stored in `SDC_SKILL.json`; the bundled helpers are tagged.
- `sdc_teach`: one entry per view (seen at several paths: *Also at*) with its documentation, own arguments without
  the depth prefix, links, buttons and forms; embedded controllers get their own section. The same knowledge is
  written as `SDC_SKILL.data.json`; the command prints the estimated token count of the skill file.
- `sdc_eval_ai --confirm deny|allow`, the task check `confirm`, size metrics (`tool_result_chars`, system prompt
  size, action rounds) and the task sets `eval/sdctest/tasks_ui` and `tasks_large` (with `fixture_large.json`).
- AI assistant: new tool `click` presses buttons and links of the current page (index from `read_page`, which now
  lists the visible buttons and links as `elements`, marked `data-ai-element` in its HTML). SDC links are resolved and
  opened with the `sdc-navigator` (`_prepareUrl` / `_handleUrl` / `goTo`); `navigate` uses `sdcNav.goTo` too. Form
  submit buttons and links leaving the app are never clicked; buttons that look like delete/save/send/logout are
  clicked only after the user allows it in the chat. Search bars (`<sdc-search-view>`) are marked
  `updates_on_change`: `fill_form` filters the list, `click` pages with "Next"/"Prev".
- AI assistant: the system prompt explains how SDC URLs are read (from the skill file, otherwise added by the
  consumer; not with `SDC_AI_SKILL_SOURCE = 'none'`).
- `sdc_teach`: the skill file starts with the section "How to read SDC URLs" (`~` segments, `N.key` arguments,
  kept arguments, relative paths). Buttons show the documented action of their `sdc_click` handler (the method's
  JSDoc) next to the observed effect, and every controller lists its "Button actions". `SDC_SKILL.json` stores
  them as `actions`; `sdc_prepare_teaching` lists undocumented button actions.
- `sdc_eval_ai`: evaluates the AI assistant. Runs task files (prompt and paraphrases, user role, start page,
  checks of the final page state, the answer and safety) for every condition (knowledge in the system prompt:
  none, apps, full, an older skill file, ...) and model against a throwaway server, drives the real
  `<sdc-ai-assistant>` in a headless browser, resets the database from a fixture before every episode and
  detects database changes, form submissions and error views. Writes one JSON line per episode (resumable),
  optionally grades rubrics with an LLM judge (Anthropic or any OpenAI-compatible model, e.g. on the KIT
  KI-Toolbox; `--judge-pending` grades the open episodes of an existing result file; a failing judge call leaves the episode `needs_judge`, and the judge is tested before the run), `--retry-errors` runs failed episodes again, and prints a summary or a
  CSV for statistics.
- AI assistant settings `SDC_AI_SKILL_SOURCE` (`auto`, `full`, `apps`, `none`), `SDC_AI_SKILL_FILE` and
  `SDC_AI_NO_SKILL_NOTE`: choose the knowledge in the system prompt. Without any knowledge the prompt now
  contains a short note telling the model to explore the page.
- AI assistant metrics: `SDC_AI_METRICS_FILE` (JSON lines) or `SDC_AI_METRICS = True` (logger
  `sdc_core.ai_metrics`) record every model request (duration, token usage, tool calls, hash of the system
  prompt) and every round of action results.
- `sdc_teach`: crawls the UI in a headless browser (Playwright) and writes `SDC_SKILL.md`, a skill file for
  AI agents: navigation tree, view arguments, buttons with their observed effects and server calls, forms,
  the SdcModel WebSocket messages of each controller, and the documented controllers and SDC models with
  their fields. Forms are filled in by the developer in a browser window, never submitted automatically.
  Missing documentation of models (docstring) and controllers (JSDoc) is asked for in the terminal and
  written into the source.
- `sdc_teach --per-app`: writes the controllers and SDC models of each app as `<app>/SDC_SKILL.json`
  without crawling. Every `sdc_teach` run uses the documentation of the installed apps' JSON files;
  `sdc_tools` and `sdc_user` ship one.
- `sdc_prepare_teaching`: prints instructions for an AI agent on how to document models and controllers,
  followed by the undocumented ones with `file:line`.
- AI assistant `<sdc-ai-assistant>` (`sdc_tools`) with the consumer `SDCAiConsumer` (route `sdc_ws/ai`):
  a chat panel that answers from the skill file and acts in the user's browser with the user's rights. It
  opens views, reads the page and fills forms (never submits) and reads SdcModel records; it cannot create,
  change or delete records. Providers: Anthropic (Claude) and any OpenAI-compatible API (e.g. the KIT
  KI-Toolbox). Users can bring their own key and choose provider, API URL, model, effort and max tokens
  in a settings menu; with the server's key the connection is fixed. The panel is movable and resizable,
  starts collapsed and renders answers as Markdown. See the new documentation page "AI assistant".
  An API URL entered by a user must resolve to public addresses, checked again on every connection (no DNS
  rebinding to internal services); the assistant's WebSocket rejects pages of other sites (`Origin`).
- Settings `SDC_AI_*` (switch, key mode, login/group rules, a daily limit of model requests per user, provider, model, API URL,
  `SDC_AI_ALLOW_USER_BASE_URL`, `SDC_AI_ADDITIONAL_SKILL_FILE`, ...), written by `sdc_init`.
- Optional extra `ai`: `pip install "simpledomcontrol[ai]"` installs `anthropic` and `openai`.
- Optional extra `teach`: `pip install "simpledomcontrol[teach]"` installs `playwright` for `sdc_teach`. It is not
  a dependency of the package itself, so production installs stay without it.
- Model WebSocket: a `load` request may carry `limit` (positive integer); the server then sends and tracks only the
  first `limit` rows. Used by `SdcQuerySet.load(query, {limit})` of sdc_client and by the assistant's `model_load`.
- New projects: `asgi.py` wraps the WebSockets in `AllowedHostsOriginValidator`, so other sites cannot open them
  with a visitor's session.
- New projects get `<sdc-ai-assistant>` in `templates/base.html` and the `sdc_ws/ai` route in `routing.py`.
- Documentation of all models and controllers of `sdc_tools`, `sdc_user` and the demo app.
- Documentation pages "Teaching AI agents" and "AI assistant".

### Fixed
- AI assistant: tool calls of the model after the round limit forced an answer are not run (no endless loop).
- AI assistant: actions and the window-resize handler ran on the temporary instance from which sdc_client builds
  the controller (`agileAggregation`), not on the controller itself.
- AI assistant: `model_load` / `model_get` with a model name that is not an SdcModel (`User`, `AuthUser`) or not
  spelled exactly (`author`) never returned: the browser waited for a model WebSocket that was never opened, and
  the answer hung until the client timed out. The server now resolves model names case-insensitively and answers
  unknown names at once with an error listing the available models (also flagged `invalid` in the metrics).
  Every browser action is also limited to 30 s and returns an error result after that.
- AI assistant: `read_page` / `fill_form` only saw fields inside a `<form>` element, so inputs like the one of
  `<sdc-password-forgotten>` or the search bar of `<sdc-search-view>` could not be filled. Such fields are now
  listed after the forms as one form per controller (`form_element: false`, `controller`) and get `input` and
  `change` events. `sdc_eval_ai` reports them in the final page state, and `expect.form` can match them by
  `controller`.
- `sdc_teach`: the skill file only documented the controllers the crawl reached, so views without a link
  (detail and edit pages, views of other roles) were missing although the apps' `SDC_SKILL.json` described
  them. They are now listed with their documentation under "Controllers not reached by the crawl".
- AI assistant: `navigate` reported success ("Now at …") even when the view showed an error page, so the model
  did not learn that a path did not exist. It now returns an error result naming the code (`404`: the view does
  not exist, `403`: not allowed) and also when the view does not finish loading in time.
- `sdc_update_links` wrote `.gitignore` without a final newline: entries added later by hand were glued to the
  last line, and the generated entry was appended again on every build.
- `SdcUser`: changing the e-mail address resets `email_confirmed` to `False` (also with
  `save(update_fields=['email'])`). Before, a user could switch to an unconfirmed address and stay
  confirmed, bypassing `SDC_USER_REQUIRE_CONFIRMED_EMAIL`.
- `sdc-password-forgotten`: an empty username/e-mail shows a hint instead of sending a server call.

### Upgrading existing projects
- Wrap the WebSocket router in `channels.security.websocket.AllowedHostsOriginValidator` in `<project>/asgi.py`
  (see "Websocket routes" in the settings documentation). Without an `Origin` header connections are then
  rejected unless `ALLOWED_HOSTS` contains `'*'`. `SDCAiConsumer` checks the origin itself in any case.
- For the AI assistant, add the `SDC_AI_*` settings you need (at least `SDC_AI_ASSISTANT = True`), the route
  `re_path(r'sdc_ws/ai', consumers.SDCAiConsumer.as_asgi())` to `<project>/routing.py` and
  `<sdc-ai-assistant></sdc-ai-assistant>` inside `<body>` of `templates/base.html`. Without the settings the
  assistant stays switched off.

## 0.159.0

### Security
- `SdcMeta.fields` / `SdcMeta.exclude` now filter the model fields in serialized output (WebSocket, REST
  and live updates). Before, they were applied to the wrong level and hid nothing. `fields = "__all__"`
  (the default) can now be combined with `exclude`.
- `SdcUser` never sends the `password` field (the password hash) to clients and does not allow filtering
  on it, whatever `SDC_USER_FIELDS` / `SDC_USER_FIELDS_EXCLUDE` say.
- The default `sdc_user_is_authorised` no longer allows everything: anyone may `connect`, `create_form`
  and `create` (self-registration); logged-in users may read and edit the rows from
  `SDC_USER_GET_QUERYSET`; `delete` and `upload` are for superusers only.
- JWT access and refresh tokens of inactive users are rejected.
- REST create, update and partial update return the saved row (serialized like a detail request) instead
  of the form's `cleaned_data`, so submitted passwords are no longer echoed. This also fixes server errors
  for forms with foreign keys or files.

### Added
- Console script `sdc` (`sdc new --name <project>`, also `python -m sdc`): creates a new project with its
  virtualenv, installs the same SDC version, runs `startproject`, `sdc_init -y` and `npm install`. Replaces
  the unpackaged `sdc/init.sh`.
- Setting `SDC_USER_REQUIRE_CONFIRMED_EMAIL` (default `False`): only users with a confirmed e-mail address
  (and superusers) can log in.
- `sdc_core.sdc_extentions.test_utils.register_test_user(username, password)` logs a test user in and
  prints its session id, so JS tests can switch users with `test_utils.login(username)` /
  `test_utils.logout()` (client 0.159.0).
- Documentation for management commands, SDC extensions, the REST API, `sdc_user`, settings and
  deployment, building the client, and testing.

### Changed
- License: MIT (before declared as Apache License 2.0, without a license file). The package now contains
  the `LICENSE` file; the client (`sdc_client`) uses the same license.

### Changed (breaking for existing projects)
- `psycopg2-binary` is no longer installed by default. Install `simpledomcontrol[postgres]` for PostgreSQL.
- New projects require `sdc_client ^0.159.0`. In 0.x versions `^0.158.x` does not include 0.159.0, so
  update the `sdc_client` range in the `package.json` of existing projects.
- The project template `Assets/tests/config/test-setup.js` defines the global `SDC_TEST_USER`, read from
  the output of the test data script. Copy the new file into existing projects to use
  `test_utils.login()`.
- Client 0.159.0: `DateField` / `DateTimeField` values are `Date` objects instead of timestamps. See
  the client changelog.
- Client 0.158.7 and later: controllers no longer receive `onInit(...)` calls. `data-*` attributes and
  navigation parameters arrive in `this.params`, readable from `onLoad()` on.

### Fixed
- JS test setup (`pre-test-setup.js`): failing `migrate`, `flush`, `loaddata` or seed-script commands stop
  the run with their error output (they were ignored); the dev DB is only exported when `JSON_DATA_DUMP` is
  set (no more file named `false`), and a failing export is a warning; the test server starts after the
  database is ready and the setup waits until it answers. `test-setup.js` fails with a message instead of
  hanging when the server does not answer.
- `register_test_user` raises an error when the login fails (it printed the session key `None`).
- The project `gulpfile.jsx` reads the `--mode` flag of the npm scripts.
- `sdc_db_tools`: `--clear` drops the tables (it crashed with a `TypeError`); `--restore` uses `loaddata`
  (one transaction, deferred foreign-key checks) instead of a retry loop that ignored errors and could loop
  forever; backups leave out content types and permissions and use natural keys, so they load into a new
  database; errors are reported as command errors.
- `sdc_shell_execute_script` requires `-s`; `sdc_new_model` reports an existing model;
  `sdc_get_controller_infos` names the missing `Assets/libs`; `sdc_cc` no longer prints the raw `-m` value;
  corrected `sdc_init -u` help text.
- `sdc_user`: the confirmation e-mail is sent once per e-mail change (it was sent on every later save);
  e-mail errors are logged instead of silently ignored, and *Password forgotten* reports them.
- `sdc_user`: `sdc-login` triggers the `login` event before the page reloads; the global `sdc-user`
  controller finishes loading for anonymous users too.
- `sdc_user`: after a password change with `password_form` the current session stays logged in.
- Server calls: normal (sync) methods work over WebSocket and may use the ORM (they run in a worker
  thread), `async def` methods also work over HTTP, return values are encoded with `DjangoJSONEncoder`,
  and a WebSocket method can reject the call by returning `{"is_error": True, "msg": ...}`. The
  `sdc_user` server methods work with both transports.
- The login view falls back to `LOGIN_SUCCESS` when no `next` parameter is posted.
- REST API: `POST`, `PUT` and `PATCH` accept JSON, form-encoded and multipart bodies (file uploads now also
  work with `PUT` / `PATCH`); `DELETE` deletes the row (was always `501`); `PUT`, `PATCH` and `DELETE`
  without id (and `POST` with id) answer `405` instead of a server error.
- `sdc_open_api` describes the real API: `{model, pk, fields}` response schemas that follow
  `SdcMeta.fields` / `exclude`, JSON / form / multipart request bodies, `200` for `POST`, `DELETE` and the
  error responses, correct formats for date-time, e-mail and URL fields, and plain YAML without
  Python-specific tags. Models without `create_form` / `edit_form` no longer make the command fail.
- Model WebSocket connections track which rows the client has received and the filter of the last full
  load separately, so form and detail requests no longer change which live updates (`on_update`,
  `on_create`, `on_delete`) are forwarded.
- `SdcModel.data_load(user, queryset, model_query)`: the declared signature now matches the call, the hook
  gets the sanitised filter, and the loaded ids for live updates are taken from its result.
- `SdcMeta` form settings may be a form class (rendering failed before), an import path or a callable,
  in the WebSocket consumer and in the REST API.
- `sdc_ws/model/<Model>/<id>` restricts the connection to that object (the id was ignored).
- WebSocket disconnect removes the connection from its channel groups (the call never ran) and calls
  `SdcMeta.on_disconnected` only if it is callable; errors there no longer block closing.
- Model names are matched in any letter case (`CaseInsensitiveDict` shared its key map between instances).
- Search forms: `_method` is optional (partial search values work), an empty `order_by` falls back to
  `DEFAULT_CHOICES`, `AbstractSearchForm(data=None)` works, `NO_RESULTS_ON_EMPTY_SEARCH` returns an empty
  queryset instead of a list.
- `channel_login` works on methods, over HTTP and WebSocket, and for `async` methods.
- `SearchableSelect` renders its `attrs`.
- The default delete message text is "… was deleted"; `except A or B` clauses catch both exceptions.
- Deleting an SDC model instance sends the new live event `on_delete` (before, deletes were sent as
  `on_update` and the row stayed in client querysets). Requires client 0.159.0.
- Generated JS model classes accept a missing `data` argument in their constructor
  (`this.setValues(data || {})`).
- New projects: the REST login route `sdc_api/login/` is registered before `sdc_api/<str:model>/`, so
  logins reach the token view (existing projects: move the line up in `urls.py`).
- New projects: `asgi.py` uses the project's settings module instead of `ElnAdapter.settings`.
- New projects: the JS test setup works without a seed script (`DB_PYTHON_SCRIPT=0`).
- `sdc-change-password` shows a real password form for the logged-in user (it was a placeholder).
- `sdc_user` e-mails: the settings template defines `HOME_URL`; if no base URL is available, the e-mail is
  skipped with a logged error instead of raising after the user is saved.
- `sdc_overwrite_lib_file` keeps the controller folder in the target path and copies only JavaScript;
  a webpack resolver plugin makes the build use files in `Assets/overwrite_libs` instead of the library
  files (before, the copies were never used).
- Settings template: a missing `ALLOWED_HOST` or an unknown `DJANGO_DATABASE` raises
  `ImproperlyConfigured` with a clear message; `ALLOWED_HOST` entries without a scheme are read as
  `https://`; other database aliases are kept; the `SDC_USER_*` comments are corrected.

### Internal
- Package metadata uses the standard `[project]` table, correct project URLs, and `poetry-core` is no longer
  a runtime dependency.
- IDE settings, a stale lock file and an empty test database are no longer tracked.
- CI runs pytest, the Django tests and the Jest tests on Python 3.13/3.14 with Node 22.
- The Jest test database no longer copies the local development database; the test data script
  creates all test data.
