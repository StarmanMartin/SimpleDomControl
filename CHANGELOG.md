# Changelog

Changes of the Python package `SimpleDomControl`. Changes of the JavaScript
runtime are listed in the
[sdc_client changelog](https://github.com/StarmanMartin/SimpleDomControlClient/blob/main/CHANGELOG.md).
The server and the client are released with the same version number.

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

### Changed (breaking for existing projects)
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
- CI runs pytest, the Django tests and the Jest tests on Python 3.13/3.14 with Node 22.
- The Jest test database no longer copies the local development database; the test data script
  creates all test data.
