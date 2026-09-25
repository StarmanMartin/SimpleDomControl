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
