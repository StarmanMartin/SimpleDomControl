.. _sdc-teaching-label:

Teaching AI agents
==================

SDC can describe a project's user interface for AI agents. The result is a
*skill file*: a Markdown document that tells an agent which views exist, how to
navigate between them, which arguments they take, what their buttons and forms
do and which data models there are. The :doc:`ai_assistant` uses it as its
knowledge about the project, and you can hand it to any other agent (for example
as a Claude Code skill).

Three management commands are involved:

``sdc_teach``
    Crawls the running UI in a headless browser and writes ``SDC_SKILL.md``.
``sdc_teach --per-app``
    Writes the controllers and SDC models of each app as ``SDC_SKILL.json``,
    without crawling.
``sdc_prepare_teaching``
    Prints instructions for an AI agent on how to document SDC models and
    controllers, followed by the list of what is still undocumented.

What the crawler cannot see is *meaning*: what a view is for, what a record
represents and what destructive actions do. That comes from the documentation of
your SDC models and controllers, which ``sdc_teach`` copies into the skill file
verbatim (see `Documenting models and controllers`_).


Creating the skill file: ``sdc_teach``
--------------------------------------

``sdc_teach`` needs Playwright and a Chromium browser. Both are only needed
where you run the command (development), not in production:

.. code-block:: sh

    $ pip install "simpledomcontrol[teach]"
    $ playwright install chromium

If no Chromium is installed, an installed Google Chrome is used, or the browser
given with ``--browser-path``.

Then run, in the directory of *manage.py*:

.. code-block:: sh

    $ python manage.py sdc_teach
    $ python manage.py sdc_teach --user admin --password secret

The command

1. migrates the database alias given with ``--database`` (default ``jest``, the
   test database, never your development database) and loads ``--fixture`` if
   given;
2. starts a throwaway ``runserver`` on a free port;
3. crawls the app anonymously: it follows every ``.navigation-links`` element
   of the ``sdc-navigator`` and clicks every button, except those that look
   destructive (delete, logout, save, submit, ...). The ``<sdc-ai-assistant>``
   panel is hidden during the crawl and is not part of the skill file;
4. with ``--user``/``--password``, crawls a second time as that user and marks
   views that need a login;
5. writes ``SDC_SKILL.md`` (or the file given with ``-o``).

Forms are never submitted automatically. When the command runs in a terminal
with a display, a browser window opens with the form highlighted: fill it in
and submit it, or click *Skip* / *Skip all forms* in the banner. The outcome of
your submit is recorded. ``--no-ask`` disables this, and also the questions
about missing documentation below.

Options:

``-o, --output``
    Output file (default ``<project>/SDC_SKILL.md``).
``--start``
    Start path of the crawl (default ``/``).
``--database``
    ``DJANGO_DATABASE`` alias of the crawl server (default ``jest``).
``--fixture``
    Fixture loaded with ``loaddata`` before crawling.
``--user``, ``--password``
    Additionally crawl as this user.
``--max-depth``, ``--max-nodes``
    Limits of the crawl (default 5 and 200).
``--no-click``
    Only follow links, do not click buttons.
``--click-all``
    Also click buttons that look destructive. Use it only with a test database.
``--deny``
    Additional regular expression of button texts or handlers that must not be
    clicked.
``--headed``
    Show the crawling browser.
``--browser-path``
    Chromium or Chrome executable.
``--timeout``
    Timeout per page action in milliseconds (default 10000).
``--no-ask``
    Never ask: no browser window for forms, no questions in the terminal.
``--per-app``
    See `Per-app skill files: --per-app`_.

The skill file contains:

- how to operate an SDC app (paths, arguments, ``window.sdcNav.goTo``,
  ``sdc_click`` handlers, when a view is ready);
- the global navigation (always visible links, buttons and forms);
- the navigation tree: every view with its path, arguments and example values,
  required URL parameters, embedded controllers, links, buttons (with handler
  and observed effect: navigation, opened controllers, server calls, alerts),
  forms (fields and the result of your submit) and the SdcModel WebSocket
  messages each controller sends;
- every controller reached, with its documentation, app, server view and
  Django URL;
- every SDC model with its documentation and the fields clients can read;
- errors observed while crawling.

Before the crawl, ``sdc_teach`` lists the undocumented SDC models and
controllers of your project and asks you for a description of each one in the
terminal. The text is written into the source code, so it is kept for the next
run. Models and controllers of installed packages are never changed.


Documenting models and controllers
----------------------------------

The skill file uses two kinds of documentation:

SDC models
    The docstring of the model class:

    .. code-block:: python

        class Book(models.Model, SdcModel):
            """
            A book in the library catalogue; one record per edition.

            - `title`, `isbn` (unique); `author` -> `Author`.
            - Readable by every logged-in user; created and edited by staff only.
            - Shown in `<book-list>`, edited in `<book-edit>`.
            """

Controllers
    The JSDoc block directly above the client class (only blank lines in
    between):

    .. code-block:: js

        /**
         * Edit form for one `Book`; opens in the detail area of `<main-view>`.
         *
         * - Arguments: `pk` (required) is the id of the book to edit.
         * - "Delete" removes the book after a confirm dialog; this cannot be undone.
         * - Requires a logged-in staff user, otherwise `sdc-error 403` is shown.
         */
        class BookEditController extends AbstractSDC {

Write for an agent that operates the UI: purpose, meaning, preconditions and
effects, in plain Markdown without headings. Do not repeat what the crawler
records anyway (lists of links, buttons and fields, URLs). Describe what the
crawler cannot find out: what records mean, who may do what, and what delete,
save, submit and logout do, because these buttons are not clicked.

``sdc_prepare_teaching`` prints these rules as a prompt for an AI agent,
followed by the undocumented models and controllers with ``file:line``:

.. code-block:: sh

    $ python manage.py sdc_prepare_teaching
    $ python manage.py sdc_prepare_teaching --all   # also the documented ones, to review them

Give its output to a coding agent, let it write the documentation, then run
``sdc_teach --no-ask``.


Per-app skill files: ``--per-app``
----------------------------------

.. code-block:: sh

    $ python manage.py sdc_teach --per-app
    $ python manage.py sdc_teach --per-app -o skills/

``--per-app`` does not crawl. It writes the controllers and SDC models of each
app with their documentation as ``<app>/SDC_SKILL.json``, for every app of the
project; with ``-o DIR`` to ``DIR/<app>/SDC_SKILL.json``, for all installed
apps:

.. code-block:: json

    {
      "app": "sdc_tools",
      "generator": "manage.py sdc_teach --per-app",
      "controllers": {
        "sdc-error": {"doc": "...", "view_class": "sdc_tools.sdc_views.SdcError",
                      "url": "/sdc_view/sdc_tools/sdc_error/<int:code>", "url_params": ["code"]}
      },
      "models": {
        "SdcUser": {"doc": "...", "fields": [{"name": "groups", "type": "ManyToManyField", "related": "Group"}]}
      }
    }

Ship this file with a reusable app: every ``sdc_teach`` run of a project that
installs the app uses its documentation, and ``sdc_prepare_teaching`` counts it
as documented. The bundled apps ``sdc_tools`` and ``sdc_user`` ship one.

Which documentation wins:

- ``sdc_teach`` (crawl): the ``SDC_SKILL.json`` of the app, if it documents the
  model or controller; otherwise the source code.
- ``sdc_teach --per-app``: the source code; the existing JSON is only kept where
  the code has no documentation.

So after changing documentation in the code, run ``sdc_teach --per-app`` again,
otherwise the crawl keeps using the old JSON text.
