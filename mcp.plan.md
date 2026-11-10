# MCP interface and API tokens for SDC projects — plan

Goal: every SDC project can expose an MCP endpoint (`/sdc_mcp/`), off by default. Through it, MCP clients
(Claude Code, Claude Desktop, Cursor, …) read and, where allowed, change SdcModel records **with the permissions of
the authenticated user, narrowed by the privileges of the token**, and receive the app knowledge written by
`sdc_teach`. Browser tools (`navigate`, `read_page`, `fill_form`, `click`) are out of scope until M6.

Precondition: the REST API (`sdc_api/`) and MCP use **revocable, listable API tokens with detailed privileges**
(M2) in place of the current stateless JWTs.

Server-only feature: no `sdc_client` change, so no protocol release in lockstep (the normal lockstep version bump
still applies). The token management UI is an `sdc_user` controller and part of its committed bundle.

## Architecture (target)

```
REST client ──Bearer token──► AdcApi (rest_api.py) ─────────────┐
MCP client  ──Bearer token──► SdcMcpView (sdc_core/mcp/view.py) ─┤
                                                                 ▼
                                   sdc_core/api_tokens.py: authenticate(request) -> (user, grant)
                                   ApiToken model (hashed, revocable, last_used, expires_at, privileges)
                                                                 │
                                                                 ▼
     sdc_extentions/model_actions.py: load / get / create / update / delete (user, grant, …)
       1. grant.allows(model, privilege)        ← token privileges (narrow only)
       2. is_authorised / get_queryset          ← user permissions (unchanged)
                                                                 │
     sdc_extentions/schema.py  ◄── also sdc_open_api             │
     sdc_core/skill_data.py    ◄── also SDCAiConsumer            ▼
                                                              database
```

Transport of MCP: **Streamable HTTP**, stateless, `application/json` responses only (no SSE), written in one
async Django view — no new dependency, runs on ASGI and WSGI, testable with the Django test client. The protocol
version(s) live in one constant.

## Current state of the API auth (what M2 replaces)

`jwt_utils.py` / `get_api_token` issue a stateless access JWT (`exp_delta_seconds`) and a refresh JWT (20×). Problems:
- Tokens can be neither listed nor revoked; only deactivating the user stops them.
- Refresh tokens are bound to `user.last_login` (±10 s): **any** new login of the user, also in the browser,
  silently invalidates all refresh tokens.
- No privileges: every token has the full rights of the user.
- `generate_jwt` sets `iat` twice in the refresh payload (the second one wins).
- The access JWT carries `iat = user.last_login`; for a user who never logged in (`None`) every API request with
  that token fails with a 500 in `jwt.decode`. `get_api_token` sets `last_login` first, so the login flow is not
  affected, but tokens made with `generate_jwt` elsewhere are (found by WP1.1).

## Decisions (accepted as proposed on 2026-11-10)

| # | Question | Proposal |
|---|---|---|
| D1 | Write/delete tools over MCP at all? (The AI assistant is read-only for models.) | Yes, but only with the matching token privilege |
| D2 | Session auth for MCP in local development? | No — tokens only |
| D3 | Separate `mcp` extra or core? | Core (no new dependency), disabled by default |
| D4 | Name of the endpoint | `sdc_mcp/` (next to `sdc_api/`) |
| D5 | Token format | Opaque tokens stored as SHA-256 hash (see WP2.1), no JWT for API access |
| D6 | Fate of `sdc_api/login/` (username/password → JWT) | Keep the URL; it issues an `ApiToken` (kind `login`, expiry, privileges from the request) and the refresh flow is dropped; old JWTs stop working after one release with a deprecation warning |
| D7 | Meaning of "account privileges" | `account:read`, `account:write`, `account:tokens` as defined in WP2.2; password, e-mail change and deleting the account are **never** possible with a token |
| D8 | Who may create tokens | Every logged-in user for themselves in the web UI; a token can only create tokens with `account:tokens` and never with more privileges than itself |

---

## M1 — Shared foundations (refactoring, no behavior change) — **done**

Status: WP1.1–WP1.4 implemented. New: `sdc_core/sdc_extentions/schema.py`, `sdc_core/sdc_extentions/model_actions.py`,
`sdc_core/skill_data.py`; tests `pytests/test_rest_api.py`, `test_open_api.py` (snapshot in
`pytests/expections/test_open_api/`), `test_model_actions.py`, `test_skill_data.py`; fixtures `django_test_db` / `db`
in `pytests/conftest.py` (in-memory test database, one transaction per test).

One intended deviation from "no behavior change": `AdcApi` now parses the request body before the permission and
existence checks, so a malformed body is answered with 400 even where 403/404 came first before.

Exit criterion: full `pytest` run green; `sdc_open_api` output and `AdcApi` responses unchanged; the AI assistant
tests (`pytests/test_ai_consumer.py`) green.

### WP1.1 — Characterization tests for the REST API
`AdcApi` / `get_api_token` have no pytest coverage today. Add `pytests/test_rest_api.py` (in-process Django,
`SdcTest` models; keep the `DJANGO_SETTINGS_MODULE` hook of `conftest.py`):
- token: login POST, refresh GET, expired / invalid token, unknown user
- `GET` list with filter, forbidden filter field (`sanitize_filter_query`), single record, 404
- `POST` / `PUT` / `PATCH` with valid and invalid form data, `DELETE`
- 401 without token, 403 when `is_authorised` refuses

Deliverable: test file. Must land **before** WP1.3. The token part of it is rewritten in M2.

### WP1.2 — `sdc_extentions/schema.py`
Move `TYPE_MAPPING`, `schema_for`, `form_field_to_schema`, `generate_form_schema`, `generate_fields_schema`,
`generate_instance_schema`, `generate_schema` and helpers out of `management/commands/sdc_open_api.py`.
`sdc_open_api` keeps only the OpenAPI document assembly and imports from the new module.

Acceptance: `sdc_open_api` produces a byte-identical YAML for `SdcTest` before/after (add a snapshot test).

### WP1.3 — `sdc_extentions/model_actions.py`
Extract the CRUD logic of `AdcApi` (`get`, `_update`, `delete`, `_patch_data`, `_serialize_instance`) into
functions that know nothing about HTTP:

```python
load(user, model_name, query, limit=None, grant=FULL) -> list[dict]
get(user, model_name, pk, grant=FULL) -> dict
create(user, model_name, data, files=None, grant=FULL) -> dict
update(user, model_name, pk, data, partial, grant=FULL) -> dict
delete(user, model_name, pk, grant=FULL) -> None
```

They raise `PermissionDenied`, `Http404` or a `FormValidationError(errors)`. `grant` is a placeholder that allows
everything until M2. `AdcApi` becomes a thin layer that maps these to `JsonResponse`s. Acceptance: WP1.1 green
without changes.

### WP1.4 — `sdc_core/skill_data.py`
Move loading/caching of the knowledge (`SDC_SKILL.md`, the apps' `SDC_SKILL.json`, `SDC_AI_ADDITIONAL_SKILL_FILE`,
the index of `SDC_AI_SKILL_MODE='index'` and the `describe` lookup) out of `SDCAiConsumer`
(`_cached_system_prompt`, `_cached_skill_data`) into a module with plain functions:

```python
skill_markdown() -> str | None
app_skills() -> dict[str, dict]
skill_index() -> str
describe(name) -> str | None
```

Acceptance: `pytests/test_ai_consumer.py` green; the consumer keeps its settings (`SDC_AI_SKILL_SOURCE`, …).

---

## M2 — Revocable API tokens with privileges — **done**

Status: WP2.1–WP2.7 implemented: `sdc_core/models.py` (`ApiToken`, migration `0001_initial`), `sdc_core/api_tokens.py`,
`sdc_core/api_urls.py`, `sdc_core/rest_api.py` (login, tokens, account), `sdc_core/admin.py`,
`manage.py sdc_tokens`, `<sdc-api-tokens>` in `sdc_user` (bundle rebuilt), OpenAPI and snapshots updated, tests in
`pytests/test_api_tokens.py` and `pytests/test_rest_api.py`. Details that differ from the text below:
- The token is looked up by its hash (unique index); no separate `compare_digest`.
- Login tokens get all privileges unless the login request narrows them; a token created through the API without
  `privileges` gets those of its creator, and its default lifetime ends with its creator's.
- `sdc_api/account/` (`GET`/`PATCH`) and `GET sdc_api/tokens/<id>/` were added to the token API.
- Deprecation (WP2.6): JWTs and the refresh flow (`GET sdc_api/login/` with a refresh JWT → login token) keep
  working for one release with `Deprecation: true`; `SDC_API_TOKENS['accept_jwt'] = False` switches them off.
  Removing `jwt_utils.py` / `JWT` is left for the release after.
- Existing projects keep their explicit `sdc_api/` routes until they switch to `include('sdc_core.api_urls')`
  (see CHANGELOG, "Upgrade").

Exit criterion: REST API works only with `ApiToken`s; a user lists and revokes their tokens in the web UI and over
the API; a revoked or expired token is refused at the next request; every model action checks the token
privileges before the user permissions; all M2 tests green.

### WP2.1 — `ApiToken` model and token format (`sdc_core`, new migration)
```
ApiToken
  id            UUID (public id, shown in lists)
  user          FK → AUTH_USER_MODEL (cascade)
  name          str  (e.g. "Claude Code laptop")
  kind          'personal' | 'login'
  prefix        str  first 8 chars of the secret, shown in lists ("sdc_3f9a1c2b…")
  secret_hash   SHA-256 of the full token (unique, indexed)
  privileges    JSON (WP2.2)
  created_at, expires_at (nullable), last_used_at, last_used_ip
  revoked_at    nullable; revoked_by FK user (nullable)
  created_by_token FK self (nullable) — chain for tokens created through the API
```
- Token string: `sdc_<prefix><random>` (`secrets.token_urlsafe(32)`), shown **once** at creation; only the hash is
  stored, so a database leak reveals no usable tokens.
- Lookup by hash, compared with `hmac.compare_digest`; `last_used_at` written at most once per minute to limit DB
  writes.
- Deactivated users (`is_active = False`) → all their tokens are refused.
- Setting `SDC_API_TOKENS = {'max_lifetime_days': 365, 'default_lifetime_days': 90, 'login_lifetime_seconds': 3600}`;
  `None` = no limit.
- Admin registration (list, filter by user, revoke action; secret never shown).

### WP2.2 — Privilege model (`sdc_core/api_tokens.py`)
Privileges are stored as a list of strings; a token **only narrows** the rights of its user, it never adds any.

| Privilege | Allows | SdcModel actions |
|---|---|---|
| `model:<Name>:read` | read records of the model | `load` |
| `model:<Name>:write` | create and change records | `create`, `save` |
| `model:<Name>:delete` | delete records | `delete` |
| `model:*:read` / `:write` / `:delete` | the same for all SdcModels | |
| `account:read` | read the own user record and own token list (secrets excluded) | |
| `account:write` | change the own profile fields that the profile form allows (no password, no e-mail) | |
| `account:tokens` | create tokens (subset of its own privileges) and revoke own tokens | |

- `write` does not imply `read`, `delete` does not imply `write`; the UI offers presets ("read only",
  "read & write", "full access").
- `Grant` object: `grant.allows(model_name, privilege) -> bool`, `grant.models(privilege) -> set` (for MCP tool
  lists); `FULL` grant for the web session and the WebSocket consumers (unchanged behavior there).
- Model names checked against `ALL_MODELS` at token creation (unknown names are refused); a model removed later
  simply grants nothing.
- The own `SdcUser` record is reachable through `account:*`; `model:SdcUser:*` keeps meaning the `SdcUser` model
  rules (`SDC_USER_GET_QUERYSET`), e.g. for admins.

### WP2.3 — Enforcement
- `api_tokens.authenticate(request) -> (user, grant)`; replaces `jwt_required` / `verify_auth_jwt`.
  Error responses: 401 missing/invalid/expired/revoked (`WWW-Authenticate: Bearer error="invalid_token"`),
  403 missing privilege (`error="insufficient_scope"`, names the needed privilege).
- `model_actions` (WP1.3) checks `grant` **before** `is_authorised` / `get_queryset`.
- `AdcApi`: `@method_decorator(jwt_required)` replaced by a decorator around `authenticate` that sets
  `request.user` and `request.api_grant`.
- OpenAPI (`sdc_open_api`): security scheme `bearerAuth`, the needed privilege per operation in the description.

### WP2.4 — Token API
| Endpoint | Method | Privilege |
|---|---|---|
| `sdc_api/tokens/` | `GET` list own tokens (id, name, prefix, privileges, dates, revoked) | `account:read` |
| `sdc_api/tokens/` | `POST` create (`name`, `privileges`, `expires_at`) → token shown once | `account:tokens` |
| `sdc_api/tokens/<id>/` | `DELETE` revoke | `account:tokens` |
| `sdc_api/tokens/current/` | `GET` the calling token itself | any valid token |
| `sdc_api/login/` | `POST` username/password → `ApiToken` kind `login` (D6) | — |

- Revocation is a soft delete (`revoked_at`), so the list keeps the history.
- `manage.py sdc_tokens list|create|revoke --user …` for admins and scripts.

### WP2.5 — Token management UI (`sdc_user`)
- New controller pair `sdc-api-tokens` generated with `sdc_cc` (do not hand-write the organizer): list of the
  user's tokens, create dialog (name, expiry, presets + per-model checkboxes read/write/delete, account
  privileges), shows the secret once with a copy button, revoke with confirmation.
- Link from the existing `sdc-user` page / `sdc-user-nav-btn`.
- Requires web login (session); creating tokens there is not limited by `account:tokens`.
- Model docstrings and JSDoc for `sdc_teach`; run `python manage.py sdc_teach --per-app --no-ask`.
- Rebuild the `sdc_user` bundle (`yarn gulp --gulpfile=Assets/gulpfile.jsx bundle --mode=production`) and copy the
  changed `*.organizer.js` / `*.style.css` into the `test_init` snapshot.

### WP2.6 — Migration and deprecation of JWT
- One release: old JWTs still accepted with a `DeprecationWarning` and a `Deprecation` response header; then
  removed together with `JWT` from `settings_extension.py.txt` and `jwt_utils.py` (`pyjwt` dependency dropped if
  nothing else uses it).
- `CHANGELOG.md`: breaking change for API clients, how to create a token.

### WP2.7 — Tests (`pytests/test_api_tokens.py`)
- Create: secret returned once, only hash stored, prefix shown; unknown model name refused; expiry above
  `max_lifetime_days` refused.
- Auth: valid, unknown, expired, revoked, deactivated user → 401; `last_used_at` updated (throttled).
- Privileges: matrix model × read/write/delete for REST; wildcard `model:*`; token never exceeds user permissions
  (user without rights + full token → 403); `write` without `read` cannot list.
- Account: list own tokens only; revoke own token, not a foreign one (404); token cannot create a token with more
  privileges than itself; password / e-mail change refused.
- Login endpoint issues a `login` token; deprecated JWT still accepted with header (until removed).

---

## M3 — Read-only MCP endpoint — **done**

Status: WP3.1–WP3.6 implemented in `sdc_core/mcp/` (`settings.py`, `view.py`, `tools.py`, `resources.py`,
`urls.py`), `model_actions.load_page`, routes in `SdcTest/urls.py` and new projects, `SDC_MCP` in the settings
template, tests in `pytests/test_mcp.py`. Checked against the official MCP Python SDK (2.3.0, protocol 2025-11-25):
initialize, tools, resources and ping work. Details that differ from the text below:
- The view is a synchronous Django view (runs under ASGI and WSGI); no `sync_to_async` needed.
- `describe` is listed only when skill data (`SDC_SKILL.data.json`) exists, like in the AI assistant.
- Deprecated JWTs are refused on MCP (API tokens only); invalid tool arguments and filters are tool results with
  `isError` (so the model can correct them), unknown or unavailable tools are JSON-RPC errors (-32602).
- `DELETE` is answered with 405 (no sessions); `resources/templates/list` returns an empty list.

Exit criterion: Claude Code connects with `claude mcp add --transport http … --header "Authorization: Bearer …"`,
lists only the tools its token allows and answers questions from `SdcTest` data; all M3 tests green.

### WP3.1 — Settings & routing
- `SDC_MCP` settings with defaults in one place (`sdc_core/mcp/settings.py`):
  ```python
  SDC_MCP = {
      'enabled': False,
      'models': '__all__',   # or a list of SdcModel names exposed over MCP at all
      'max_records': 50,
  }
  ```
- Optional per-model override `SdcMeta.mcp = False` (never exposed, whatever the token says).
- Route `path('sdc_mcp/', SdcMcpView.as_view())`: add it to `init_add/sdc_core_manager.py` (new projects) and to
  `SdcTest/urls.py`. The view answers 404 while `enabled` is False.
- Update the `test_init` snapshot (`pytests/expections/test_init/…`) for the changed `urls.py` /
  `settings.py`; add the commented-out `SDC_MCP` block to `template_files/settings_extension.py.txt`.

### WP3.2 — JSON-RPC transport (`sdc_core/mcp/view.py`)
- `POST` only (`GET` → 405, no SSE stream); `csrf_exempt`.
- Parse JSON-RPC 2.0: request, notification (→ 202 without body), parse error, invalid request, method not found.
- `initialize`: protocol version negotiation, `serverInfo` (project name, SDC version), capabilities
  `tools` and `resources`, `instructions` (short project description + skill index from WP1.4).
- `ping`, `notifications/initialized`.
- `Origin` check against `ALLOWED_HOSTS` (DNS-rebinding protection required by the spec); requests without
  `Origin` (non-browser clients) are allowed.
- Sync ORM work wrapped with `sync_to_async`.

### WP3.3 — Authentication
- `api_tokens.authenticate` (WP2.3); 401 with `WWW-Authenticate: Bearer` as for REST.
- The token's user and grant apply to every tool call.

### WP3.4 — Read tools (`sdc_core/mcp/tools.py`)
| Tool | Input | Annotations | Listed when |
|---|---|---|---|
| `describe` | `name`: view, controller tag or model name | `readOnlyHint` | always |
| `model_get` | `model` (enum of readable models), `id` | `readOnlyHint` | any `model:…:read` |
| `model_load` | `model`, `filter` (Django lookups), `limit` (≤ `max_records`) | `readOnlyHint` | any `model:…:read` |
| `account_get` | — | `readOnlyHint` | `account:read` |

- The `model` enum contains only models exposed by `SDC_MCP['models']` **and** readable by the token.
- Execution through `model_actions` with the token's grant → same checks as REST.
- Tool errors (403, 404, bad filter) as results with `isError: true` and a readable message; JSON-RPC errors only
  for protocol faults (unknown tool, schema-invalid arguments).
- `model_load` reports `total` and whether the result was cut by `limit`.

### WP3.5 — Resources (`sdc_core/mcp/resources.py`)
- `sdc://skill` — full skill file (if present)
- `sdc://skill/<app>` — each app's `SDC_SKILL.json`
- `sdc://openapi` — OpenAPI document (generated at runtime from WP1.2, YAML)

### WP3.6 — Tests (`pytests/test_mcp.py`)
- Protocol: initialize / version negotiation, notification → 202, unknown method, malformed JSON, `GET` → 405,
  disabled → 404, foreign `Origin` → 403.
- Auth: no token / expired / revoked token → 401.
- Tools: `tools/list` depends on the token privileges and `SDC_MCP['models']`; `model_load` respects
  `get_queryset`, filters and `limit`; forbidden record → `isError`; `describe` known / unknown name.
- Resources: list and read.

---

## M4 — Write and delete tools — **done**

Status: WP4.1–WP4.2 implemented in `sdc_core/mcp/tools.py` (tools now carry their handler; write tools are built
from the models' forms), `api_tokens.update_account` shared by `sdc_api/account/` and `account_update`, tests in
`pytests/test_mcp.py` (incl. the schema parity with the OpenAPI description). Checked with the official MCP Python
SDK: create, invalid values, update and delete. Details that differ from the text below:
- Tool names are the model name in snake case: `BookContent` → `book_content_create`.
- `<model>_update` is marked `destructiveHint` (it overwrites values) as well as `idempotentHint`.
- A model whose create form has a required file field gets no create tool (MCP cannot send files).
- Values of write tools are not type-checked against the schema: the form validates them and returns its errors,
  which tells the model more than a type error. Required and unknown argument names are checked first.

Prerequisite: decision D1 = yes. Exit criterion: create / update / delete through MCP for an `SdcTest` model
behave exactly like the REST API, including form validation; tools appear only for tokens with the privilege.

### WP4.1 — Per-model write and delete tools
| Tool | Input schema | Annotations | Listed when |
|---|---|---|---|
| `<model>_create` | `generate_form_schema(create_form)` | — | `model:<Name>:write` |
| `<model>_update` | `id` + `generate_form_schema(edit_form, partial=True)` | `idempotentHint` | `model:<Name>:write` |
| `<model>_delete` | `id` | `destructiveHint` | `model:<Name>:delete` |
| `account_update` | profile form schema (no password, no e-mail) | `idempotentHint` | `account:write` |

- Only generated when the matching form exists (`resolve_form`).
- File fields are excluded from the schema in v1.
- Form errors returned as `isError` result with the field → messages map.

### WP4.2 — Tests
Allowed / missing privilege / no form / validation error / user permission refused / delete of a foreign record;
schema parity test: tool input schemas equal the OpenAPI request schemas of the same model.

---

## M5 — Developer experience, docs, release

Exit criterion: a fresh `sdc_init` project gets a working MCP endpoint by setting `SDC_MCP['enabled'] = True`,
creating a token in the web UI and following the docs; released in lockstep.

### WP5.1 — `sdc_mcp_config` management command
Prints a ready `claude mcp add --transport http …` command and an `.mcp.json` snippet with the URL; with
`--user` and `--privileges` creates the token through `sdc_tokens`.

### WP5.2 — Documentation
- `DOCUMENTATION.md` (root): sections "API tokens & privileges" and "MCP interface" — settings, token lifecycle,
  privilege table, tools, resources, security notes.
- Sphinx docs (`docs/`): settings reference; run `docs/build_docs.sh`.
- `AGENTS.md`: gotchas (snapshot of `test_init`, modules shared by REST / AI / MCP, tokens narrow but never widen
  user permissions).
- `CHANGELOG.md` entry (breaking change of the API auth from M2).

### WP5.3 — Release
Bump versions with `yarn update_version` (`pyproject.toml`, `package.json`) and set the client's `package.json`
by hand; no client runtime change. M2 can be released on its own before M3/M4.

---

## M6 — Later (optional, separate planning)

- **WP6.1 OAuth 2.1** — protected resource metadata (`/.well-known/oauth-protected-resource`) and an authorization
  server (e.g. `django-oauth-toolkit` as an optional extra) for clients that only support OAuth; OAuth scopes map
  1:1 to the privileges of WP2.2 and the issued tokens are `ApiToken`s (kind `oauth`), so they appear in the same
  list and can be revoked there.
- **WP6.2 Rate limiting** — per token, analogous to `SDC_AI_MAX_REQUESTS_PER_USER`.
- **WP6.3 Server calls as tools** — expose documented server-call methods of `SDCView`s (WebSocket `SDCConsumer`
  channel) where docstrings/type hints allow a schema; new privilege `call:<view>`.
- **WP6.4 File fields** — upload/download of `FileField`s (base64 or presigned URLs).
- **WP6.5 UI bridge** — forward `navigate` / `read_page` / `fill_form` / `click` to an open browser session of the
  same user through `SDCAiConsumer`, with the same confirmation rules as the assistant.
- **WP6.6 Audit log** — per token: which tool / endpoint changed which record.

## Dependencies

```
WP1.1 ──► WP1.3 ──► WP2.3 ──┬──► WP2.4 ──► WP2.5
WP2.1 ──► WP2.2 ────┘       │
                            ├──► WP3.3 ──► WP3.4 ──► WP4.1 ──► WP4.2
WP1.2 ──────────────────────┤        ▲
WP1.4 ──► WP3.5             │        │
WP3.1 ──► WP3.2 ────────────┴────────┘
WP2.* ──► WP2.6, WP2.7
M2 + M3 + M4 ──► M5
```

## Risks

| Risk | Mitigation |
|---|---|
| Breaking existing API clients (JWT removal) | D6: one release with both; deprecation header; changelog with migration steps |
| Token leak | only hashes stored; shown once; expiry by default; revoke in UI; prefix allows identifying leaked tokens |
| Privileges widen access by mistake | grant check **and** user check in one place (`model_actions`); test matrix in WP2.7; `FULL` grant only for session / WebSocket |
| DB load from token lookups | indexed hash lookup; `last_used_at` throttled |
| MCP spec changes (hand-written transport) | version in one constant; protocol tests; small surface (no SSE, no sessions) |
| Refactoring changes REST / AI behavior | WP1.1 characterization tests and the OpenAPI snapshot before moving code |
| Too many tools with many models | generic read tools; per-model tools only for privileged write/delete models |
| `test_init` / bundle snapshot drift | update snapshots in WP2.5 and WP3.1 in the same commit |
