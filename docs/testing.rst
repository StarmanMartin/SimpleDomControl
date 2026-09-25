.. _sdc-testing-label:

Testing
=======

An SDC project has two kinds of tests:

- Python tests for views, models and permissions, run with Django's test
  runner.
- JavaScript tests for controllers, run with jest against a real Django test
  server.

Python tests
------------

Write normal Django tests in ``<app>/tests.py`` and run them with:

.. code-block:: sh

   python manage.py test

The test database is created from the ``default`` database, which is the one
selected by ``DJANGO_DATABASE`` (see :ref:`sdc-settings-label`).

JavaScript tests
----------------

Run the jest tests with:

.. code-block:: sh

   npm run sdc_test

This runs ``NODE_OPTIONS=--experimental-vm-modules jest``. The jest
configuration is in the root ``package.json``:

- ``testMatch`` is ``<rootDir>/*/Assets/tests/*.test.js?(x)``. Tests live in
  ``<app>/Assets/tests/`` of each project app. The links in
  ``Assets/tests/`` are not matched, so every test runs once.
- ``testEnvironment`` is ``jest-environment-jsdom`` with the URL
  ``http://127.0.0.1:8765``. Relative requests of the client go to the test
  server on that port.
- Files are transformed with ``babel-jest`` and ``Assets/babel.config.json``,
  so tests can use JSX.
- ``globalSetup`` is ``Assets/tests/config/pre-test-setup.js``,
  ``setupFilesAfterEnv`` is ``Assets/tests/config/test-setup.js`` and
  ``globalTeardown`` is ``Assets/tests/config/post-test-teardown.js``.

The tests import the controllers from ``Assets/src`` and ``Assets/libs``.
Those links and ``Assets/src/models/`` are created by ``link_files``, so run
``npm run build`` (or ``npm run develop``) at least once before the tests (see
:ref:`sdc-build-label`).

Generated tests
^^^^^^^^^^^^^^^

When ``sdc_cc`` creates the first controller of an app, it also creates
``<app>/Assets/tests/<app>.test.js`` with the imports:

.. code-block:: javascript

   import {test_utils} from 'sdc_client';
   import {} from "#root/src/main_app/main_app.organizer.js";
   import '#root/libs/sdc_tools/sdc_tools.organizer.js'
   import '#root/libs/sdc_user/sdc_user.organizer.js'
   import '#root/src/models/src.js'

For every controller, ``sdc_cc`` appends a test that loads the controller:

.. code-block:: javascript

   describe('BookList', () => {
       let controller;

       beforeEach(async () => {
           // Create new controller instance based on the standard process.
           controller = await test_utils.get_controller('book-list',
                                                     {},
                                                     '<div><h1>Controller Loaded</h1></div>');
       });

       test('Load Content', async () => {
           const $div = $('body').find('book-list');
           expect($div.length).toBeGreaterThan(0);
       });

   });

Configuration files
^^^^^^^^^^^^^^^^^^^

The test setup reads two dotenv files:

``Assets/.sdc_python_env``
    ``PYTHON`` is the Python interpreter used for all ``manage.py`` calls.
    ``sdc_core`` writes this file with its own interpreter on every Django
    start with ``DEBUG = True``. It is added to ``.gitignore``. If ``PYTHON``
    is missing, the test setup fails with
    ``The environment PYTHON is not set``.

``Assets/.sdc_env``
    Controls the test database. On every Django start with ``DEBUG = True``,
    ``sdc_core`` adds missing keys with their defaults and keeps existing
    values. This file is not added to ``.gitignore``; commit it.

    .. code-block:: sh

       JSON_DATA_DUMP="Assets/tests/dumps/test_data_dump.json"
       COPY_DEFAULT_DB=1 # 0 for false or 1 for true
       DB_PYTHON_SCRIPT=0 # Add path to pythonscript to prepare DB

    ``JSON_DATA_DUMP``
        Path of a JSON fixture. If the file exists, it is loaded into the test
        database. ``0`` disables loading.

    ``COPY_DEFAULT_DB``
        Any value other than ``0`` dumps the development database to
        ``JSON_DATA_DUMP`` before each run (``dumpdata --exclude
        auth.permission --exclude contenttypes``). The tests then depend on
        your local data and can behave differently on other machines and in
        CI. Use ``0`` to keep the test data reproducible; a committed fixture
        at ``JSON_DATA_DUMP`` is still loaded.

    ``DB_PYTHON_SCRIPT``
        Path of a seed script that is run in the test database (see
        `Seed script`_). ``0`` disables it.

A typical ``Assets/.sdc_env`` with reproducible data:

.. code-block:: sh

   JSON_DATA_DUMP=0
   COPY_DEFAULT_DB=0
   DB_PYTHON_SCRIPT="Assets/tests/data_scripts/test_prepare_data_script.py"

What happens before the tests
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``pre-test-setup.js`` runs once before all test files:

1. Loads ``Assets/.sdc_env`` and ``Assets/.sdc_python_env``.
2. If ``COPY_DEFAULT_DB`` is not ``0``: runs ``manage.py dumpdata`` on the
   development database into ``JSON_DATA_DUMP``.
3. Sets ``DJANGO_DATABASE=jest``. All following commands and the server use
   the ``jest`` database (``test_db.sqlite3``).
4. Starts ``manage.py runserver 8765`` in the background. Its output goes to
   ``Assets/tests/logs/jest_server_logs_<date>.log``.
5. Waits one second, then runs ``manage.py migrate`` and
   ``manage.py flush --no-input``.
6. If ``JSON_DATA_DUMP`` is set and the file exists: runs
   ``manage.py loaddata <JSON_DATA_DUMP>``.
7. If ``DB_PYTHON_SCRIPT`` is set: runs
   ``manage.py sdc_shell_execute_script -s <DB_PYTHON_SCRIPT>`` and stores its
   output in ``SCRIPT_OUTPUT``. The output is printed.

.. note::

   The output of ``dumpdata``, ``migrate``, ``flush`` and ``loaddata`` is not
   shown, and failures of these commands do not stop the run. If tests fail
   unexpectedly, run the commands by hand with ``DJANGO_DATABASE=jest``. If
   the seed script fails, its error message is printed as ``SCRIPT_OUTPUT``.

``test-setup.js`` runs before each test file:

- ``SCRIPT_OUTPUT``: the seed script output as an array of lines.
- ``SDC_TEST_USER``: an object that maps user names to session keys, built
  from the ``USER_FOR_SDC_TESTS$$$<username>$$$<session_key>`` lines of the
  seed script output.
- ``gettext``: returns its argument.
- Adds ``File.prototype.arrayBuffer`` and ``File.prototype.text`` to jsdom if
  missing.
- Loads ``/`` from the test server and evaluates every line that starts with
  ``window.``. This sets ``window.CSRF_TOKEN``, ``window.DEBUG``,
  ``window.SERVER_CALL_VIA_WEB_SOCKET``, ``window.VERSION`` and
  ``window.LANGUAGE_CODE`` from ``templates/base.html``.
- Globals ``$`` (jQuery), ``_`` (lodash), ``_sdc`` (all exports of
  ``sdc_client``), ``jest``, ``TextEncoder`` and ``TextDecoder``.

``post-test-teardown.js`` stops the test server after all tests.

Seed script
^^^^^^^^^^^

The seed script is plain Python. ``sdc_shell_execute_script`` runs it with
``exec`` inside the Django environment, so models and settings are available.
Create test data and register the users the tests log in with:

.. code-block:: python

   # Assets/tests/data_scripts/test_prepare_data_script.py
   from django.contrib.auth import get_user_model

   from main_app.models import Author, Book
   from sdc_core.sdc_extentions.test_utils import register_test_user

   User = get_user_model()

   author = Author.objects.create(name='Martin', age=22)
   Book.objects.create(title='My super Book', author=author)

   User.objects.create_superuser("TestUser", "test@test.test", "123")
   register_test_user(username="TestUser", password="123")

``register_test_user(username, password)`` logs in with Django's test
``Client`` and prints ``USER_FOR_SDC_TESTS$$$<username>$$$<session_key>``.
``test-setup.js`` turns these lines into ``SDC_TEST_USER``. Call it after the
user has been created. With wrong credentials the printed session key is
``None``.

Client test utilities
^^^^^^^^^^^^^^^^^^^^^

``sdc_client`` exports ``test_utils``:

``test_utils.get_controller(tag_name, init_arguments = {}, origen_html = '')``
    Clears ``<body>``, inserts ``<tag_name>origen_html</tag_name>``, sets each
    entry of ``init_arguments`` as jQuery data on the tag (like ``data-*``
    attributes), runs the normal SDC lifecycle and resolves with the
    controller instance.

``test_utils.controllerFromTestHtml(html, afterLifecycle = null)``
    Clears ``<body>``, appends ``html``, runs the SDC lifecycle and resolves
    with all controllers in the page. If ``afterLifecycle`` is truthy, it
    resolves after the first controller has run ``onRefresh``.

``test_utils.getCsrfToken()``
    Returns the value of the ``csrftoken`` cookie, or an empty string.

``test_utils.login(user)``
    Sets the ``sessionid`` cookie to ``SDC_TEST_USER[user]``. Returns
    ``false`` and removes the cookie if the user was not registered by the
    seed script.

``test_utils.logout()``
    Removes the ``sessionid`` cookie.

``get_controller`` and ``controllerFromTestHtml`` replace ``$.ajax`` with a
``jest.spyOn`` wrapper. The wrapper returns failed requests as resolved
promises, so a failing request does not reject in the test.

A complete test file:

.. code-block:: javascript

   /**
    * @jest-environment jsdom
    */

   import {test_utils} from 'sdc_client';
   import {} from "#root/src/models/src.js";
   import {} from "#root/src/main_app/main_app.organizer.js";
   import '#root/libs/sdc_tools/sdc_tools.organizer.js';
   import '#root/libs/sdc_user/sdc_user.organizer.js';

   describe('BookList as logged-in user', () => {
       let controller;

       beforeAll(async () => {
           test_utils.login('TestUser');
           controller = await test_utils.get_controller('book-list',
               {authorId: 1},
               '<div><h1>Controller Loaded</h1></div>');
       });

       test('renders the tag', () => {
           expect($('body').find('book-list').length).toBe(1);
       });

       test('server call', async () => {
           const res = await controller.serverCall('call_echo', {a: 1});
           expect(res).toStrictEqual({a: 1});
       });
   });

   describe('Test users', () => {
       test('unknown users are not logged in', () => {
           expect(test_utils.login('NoSuchUser')).toBe(false);
           test_utils.logout();
       });
   });

``call_echo`` stands for a server method of the ``BookList`` view that
returns its arguments (see :doc:`sdc_controller`).

Continuous integration
----------------------

The JavaScript tests need Python and Node. In CI, ``Assets/.sdc_python_env``
does not exist (it is ignored by git), and the links created by ``link_files``
are missing. Write the interpreter path first and build before running the
tests. A GitHub Actions job based on the SDC repository's own workflow:

.. code-block:: yaml

   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
       - uses: actions/checkout@v4

       - uses: actions/setup-python@v5
         with:
           python-version: "3.13"

       - uses: actions/setup-node@v4
         with:
           node-version: 22.x

       - name: Install Python dependencies
         run: pip install -r requirements.txt

       - name: Point the JS build and tests to the interpreter
         run: echo "PYTHON=\"$(which python)\"" > Assets/.sdc_python_env

       - name: Install JS dependencies
         run: npm ci

       - name: Run Django tests
         run: python manage.py test

       - name: Build JS assets (creates links and model classes)
         run: npm run build

       - name: Run JS tests
         run: npm run sdc_test

Commit ``Assets/.sdc_env`` with ``COPY_DEFAULT_DB=0`` and a seed script, so
CI does not depend on a development database.
