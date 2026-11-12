---
name: sdc-testing
description: Testing and debugging SimpleDomControl (SDC) projects — use when writing or running Django or Jest tests, checking a controller's HTML or a server call without a browser, or reading test and build failures.
---

# Testing SDC projects

```
python manage.py sdc_agent check                 # static problems first (fast, no tests)
python manage.py sdc_agent test [app_or_label]   # Django tests: summary + failures, log in .sdc_agent/logs/
python manage.py sdc_agent test --js             # Jest tests of the controllers (needs node_modules)
python manage.py sdc_agent build                 # asset build errors only
```

## Django tests without a browser

Controllers and server calls are plain HTTP requests:

```python
import json
from django.test import TestCase


class BookListTest(TestCase):
    def test_content(self):
        response = self.client.get('/sdc_view/library/book_list', {'_method': 'content'})
        self.assertEqual(response.status_code, 200)
        html = json.loads(response.content)['html']          # {"html": ..., "data": ...}
        self.assertIn('<li>Dune</li>', html)

    def test_server_call(self):
        response = self.client.post('/sdc_view/library/book_detail', {
            '_method': 'sdc_server_call', '_sdc_func_name': 'count_books', 'data': json.dumps({})})
        self.assertEqual(json.loads(response.content)['_return_data'], 0)
```

- A view with `SdcLoginRequiredMixin` answers `301` with a JSON redirect when logged out: `self.client.force_login(user)`.
- Models: create records in the test, then call the forms (`Model.SdcMeta.create_form`) or the REST API.

## Jest tests (client controllers)

`sdc_agent new-controller` adds a test stub to `<app>/Assets/tests/<app>.test.js`. `yarn sdc_test` / `npm run
sdc_test` migrates and seeds a separate `jest` database, starts `manage.py runserver` on **127.0.0.1:8765** (stop
other servers on that port) and needs `PYTHON` in `Assets/.sdc_python_env` (written by `manage.py` in
DEBUG when it is missing). Helpers: `test_utils.get_controller(tag, {args}, html)` from `sdc_client`.

## Reading failures

- `sdc_agent test` prints at most a few lines per failure; open the log path it prints for the full traceback.
- A controller shows nothing in the browser: run `sdc_agent check`, then `sdc_agent build` (old bundle).
