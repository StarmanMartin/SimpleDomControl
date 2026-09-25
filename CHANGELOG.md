# Changelog

Changes of the Python package `SimpleDomControl`. Changes of the JavaScript
runtime are listed in the
[sdc_client changelog](https://github.com/StarmanMartin/SimpleDomControlClient/blob/main/CHANGELOG.md).
The server and the client are released with the same version number.

## 0.159.0

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
- Generated JS model classes accept a missing `data` argument in their constructor
  (`this.setValues(data || {})`).

### Internal
- CI runs pytest, the Django tests and the Jest tests on Python 3.13/3.14 with Node 22.
- The Jest test database no longer copies the local development database; the test data script
  creates all test data.
