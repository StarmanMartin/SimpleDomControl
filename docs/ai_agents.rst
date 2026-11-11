.. _sdc-ai-agents-label:

Working with AI coding agents
=============================

SDC projects come prepared for AI coding agents such as Claude Code, Codex or
Cursor: a short ``AGENTS.md`` tells the agent how the project is built, skills
explain the framework on demand, and ``manage.py sdc_agent`` answers questions
about the project in a few lines and does the multi-file work. In a benchmark
of six typical SDC tasks this cut the input tokens of the agent by 63 % and the
cost by half, at the same success rate (see *projects/agents-bench/* in the
repository).

The agent kit
-------------

``sdc_init`` writes (skip it with ``--no-agent-kit``):

*AGENTS.md*
   Always loaded by the agent (about 800 tokens): the controller-pair
   structure, the ``sdc_agent`` commands, the rules that save the most work
   (create controllers and models with the commands, no arrow functions as
   event handlers in the constructor, how server calls work, finish with
   ``sdc_agent check``) and a list of the skills. A block between
   ``<!-- sdc:generated:start … -->`` and ``<!-- sdc:generated:end -->`` lists
   the apps and models of the project; edit the rest of the file freely.

*CLAUDE.md*
   ``@AGENTS.md`` (Claude Code reads ``CLAUDE.md``). An existing file is kept
   and only gets this line.

*.claude/skills/*
   Skills the agent loads only when a task needs them:

   - ``sdc-controller`` — views, templates, client controllers, events, server
     calls, navigation
   - ``sdc-model`` — SdcModels, forms, permissions, migrations, querysets
   - ``sdc-api-mcp`` — REST API, API tokens, MCP endpoint
   - ``sdc-testing`` — Django and Jest tests, debugging
   - ``sdc-ai-knowledge`` — documenting models and controllers for the AI
     assistant (``sdc_teach``)

Keep the kit current after an SDC upgrade:

.. code-block:: sh

   python manage.py sdc_agent kit check     # outdated or missing files
   python manage.py sdc_agent kit update    # edited files are kept
   python manage.py sdc_agent kit install   # in projects created before 0.164.0

``sdc_agent check`` also warns when the kit is older than the installed SDC.

``manage.py sdc_agent``
-----------------------

All sub-commands answer in a few lines with paths relative to the project and
never ask for input.

``overview [--app APP] [--all] [--json]``
   Apps, controllers (tag, URL, view ``file:line``, JS folder) and SdcModels
   (fields, forms) of the project, one line each. Installed apps such as
   ``sdc_tools`` are summarized unless ``--all``.

``where NAME [--json]``
   Every file of one controller (tag or snake_case name) or model: view class
   and line, URL, template, JS, SCSS, organizer line, JS tests, forms.

``check [--strict] [--json]``
   Consistency problems, each with its fix: a controller missing in the app
   organizer, a ``contentUrl`` that does not match the view, a missing template
   or ``app.register``, an arrow function registered as event handler in the
   constructor, form paths that cannot be imported, an outdated agent kit, and
   missing documentation (counts as failure only with ``--strict``). Exit code
   1 when there are problems.

``new-controller APP NAME [--mixins a,b]`` / ``new-model APP Name``
   Run ``sdc_cc`` / ``sdc_new_model`` and list the created (``+``) and changed
   (``~``) files and the next steps.

``test [--js] [--all] [ARG …]`` / ``build [--develop]``
   Run the Django tests, the Jest tests (``yarn``/``npm run sdc_test``) or the
   asset build and print only the summary and the failures; the full log is in
   *.sdc_agent/logs/* (git-ignored). Without *node_modules* Jest and the build
   report "not run" instead of failing.

``kit install|update|check``
   The agent kit, see above.

Commands without prompts
------------------------

Outside a terminal — always the case for agents and scripts — ``sdc_cc``,
``sdc_new_model`` and ``sdc_init`` never wait for input: a missing argument
fails with the flag to pass (``sdc_cc`` without ``-m`` uses no mixins,
``sdc_init`` answers *no* unless ``-y``).

Runtime agents
--------------

The AI assistant and MCP clients get the knowledge of ``sdc_teach``
(:doc:`teaching`). MCP keeps its answers small: the server instructions contain
only the exposed data models (``SDC_MCP['instructions']``), and ``model_load``
/ ``model_get`` (or ``?_fields=`` in the REST API) return only the fields asked
for. See :doc:`mcp`.
