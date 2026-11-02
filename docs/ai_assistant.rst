.. _sdc-ai-assistant-label:

AI assistant
============

``<sdc-ai-assistant>`` (app ``sdc_tools``) is a chat panel that helps users to
use your site. It answers questions about the site and acts on the page in the
user's browser: it opens views, reads the current page, enters values into
forms and reads SdcModel records. It knows the site from the skill file written
by ``sdc_teach`` (see :doc:`teaching`).

The assistant has the rights of the logged-in user and no more. It cannot
create, change or delete records and never submits a form: it fills forms, and
the user checks and submits or saves them.


Setup
-----

1. Install the provider SDKs (``anthropic`` and ``openai``):

   .. code-block:: sh

      pip install "simpledomcontrol[ai]"

2. Enable the assistant in ``settings.py``:

   .. code-block:: python

      SDC_AI_ASSISTANT = True

3. Choose who pays for the requests (see `API key`_). For a key of the server,
   set ``SDC_AI_TOKEN_FROM_SYSTEM = True`` and the provider's environment
   variable, e.g. ``ANTHROPIC_API_KEY``.

4. Give the assistant its knowledge: run ``python manage.py sdc_teach`` (see
   :doc:`teaching`).

Projects created with ``sdc_init`` already have the ``<sdc-ai-assistant>`` tag
in ``templates/base.html``, the WebSocket route ``sdc_ws/ai`` in
``<project>/routing.py`` and all ``SDC_AI_*`` settings. For older projects add:

.. code-block:: html

   <!-- templates/base.html, inside <body> -->
   <sdc-ai-assistant></sdc-ai-assistant>

.. code-block:: python

   # <project>/routing.py
   re_path(r'sdc_ws/ai', consumers.SDCAiConsumer.as_asgi()),

The panel renders nothing while ``SDC_AI_ASSISTANT`` is ``False`` or missing.


API key
-------

``SDC_AI_TOKEN_FROM_SYSTEM = True``
    Every user uses the server's key. The provider SDK reads it from the
    environment: ``ANTHROPIC_API_KEY`` for ``anthropic``, ``OPENAI_API_KEY`` for
    ``openai-compatible``. The assistant then always requires a login, even if
    ``SDC_AI_REQUIRE_LOGIN`` is ``False``, so anonymous visitors cannot use
    your key. ``SDC_AI_MAX_REQUESTS_PER_USER`` limits the requests per user and
    day. Users cannot change the connection: the settings menu only shows the
    provider and model.

``SDC_AI_TOKEN_FROM_SYSTEM = False`` (default)
    Every user enters their own key in the settings menu (⚙). The server keeps
    the key in memory for the open connection only; it is never stored or sent
    back. "Remember on this device" keeps it in the browser's ``sessionStorage``
    until the tab is closed (the other settings in ``localStorage``).


Providers
---------

``anthropic`` (default)
    Claude models through the Anthropic API, e.g. ``claude-opus-5-5`` (default),
    ``claude-sonnet-5-5`` or ``claude-haiku-5-5``. Uses prompt caching for the
    skill file, ``SDC_AI_EFFORT``, and the server-side refusal fallback of the
    current models.

``openai-compatible``
    OpenAI and every API that speaks the OpenAI chat completions format, for
    example the KIT KI-Toolbox, a LiteLLM proxy or a local Ollama. Set the API
    URL and the model; ``SDC_AI_EFFORT`` is not used.

    .. code-block:: python

       SDC_AI_PROVIDER = 'openai-compatible'
       SDC_AI_BASE_URL = 'https://ki-toolbox.scc.kit.edu/api/v1'
       SDC_AI_MODEL = 'GPT-OSS:120b'

With their own key, users can choose the provider, API URL, model, effort and
maximum answer length in the settings menu. Changing the provider starts a new
conversation. A user's API URL must be ``https`` and resolve only to public
addresses (no ``localhost`` or private networks), because the server sends the
requests with the key there. The check runs when the settings are saved and
again for every connection to the API, which goes to exactly the checked
address (no proxies from the environment, no redirects), so a host name whose
DNS answer changes later cannot reach internal addresses either.
``SDC_AI_ALLOW_USER_BASE_URL = False`` disables the field.

When the provider rejects a request (wrong key, URL, model or API format), the
user sees the HTTP status, the requested URL and a hint, and the settings menu
opens. With the server's key, the URL is not shown.


Settings
--------

All settings are optional; projects without them have the assistant switched
off. The ``settings.py`` written by ``sdc_init`` reads ``SDC_AI_PROVIDER``,
``SDC_AI_MODEL``, ``SDC_AI_BASE_URL``, ``SDC_AI_MAX_TOKENS``, ``SDC_AI_TIMEOUT``,
``SDC_AI_MAX_RETRIES`` and ``SDC_AI_EFFORT`` from environment variables of the
same name.

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Setting
     - Default
     - Meaning
   * - ``SDC_AI_ASSISTANT``
     - ``False``
     - Switches the assistant on.
   * - ``SDC_AI_TOKEN_FROM_SYSTEM``
     - ``False``
     - ``True``: the server's key for everybody; ``False``: every user's own key.
   * - ``SDC_AI_REQUIRE_LOGIN``
     - ``True``
     - Only logged-in users may use the assistant (always on with the
       server's key).
   * - ``SDC_AI_ALLOWED_GROUPS``
     - ``None``
     - List of group names allowed to use the assistant; staff and superusers
       always are. ``None``: all users.
   * - ``SDC_AI_MAX_REQUESTS_PER_USER``
     - ``100``
     - Model requests per user and day on the server's key (a prompt whose
       answer uses tools makes one request per tool round); ``None``: unlimited.
       Counted in Django's cache: use a shared cache (e.g. Redis) when you run
       several server processes.
   * - ``SDC_AI_PROVIDER``
     - ``'anthropic'``
     - ``'anthropic'`` or ``'openai-compatible'``.
   * - ``SDC_AI_MODEL``
     - ``'claude-opus-5-5'``
     - Model id of the provider.
   * - ``SDC_AI_BASE_URL``
     - ``''``
     - API URL; empty: the provider's default. Not shown to users.
   * - ``SDC_AI_ALLOW_USER_BASE_URL``
     - ``True``
     - Users with their own key may set an API URL.
   * - ``SDC_AI_MAX_TOKENS``
     - ``16000``
     - Maximum length of one model response.
   * - ``SDC_AI_TIMEOUT``, ``SDC_AI_MAX_RETRIES``
     - ``600``, ``2``
     - Request timeout in seconds and retries of the provider SDK.
   * - ``SDC_AI_EFFORT``
     - ``'medium'``
     - Claude only: ``low``, ``medium``, ``high``, ``xhigh`` or ``max``.
   * - ``SDC_AI_ADDITIONAL_SKILL_FILE``
     - ``None``
     - Path or list of paths (relative to ``BASE_DIR``) of hand-written
       knowledge files, appended to the skill file.
   * - ``AI_DEFAULT_SYSTEM_PROMPT``
     - not set
     - Replaces the built-in instructions of the assistant
       (``sdc_core.consumers.AI_DEFAULT_SYSTEM_PROMPT``).


What the assistant knows
------------------------

The system prompt of every conversation consists of:

1. the instructions (``AI_DEFAULT_SYSTEM_PROMPT``): how to use the tools, to
   answer briefly, to use only views, models and fields from the context, and a
   link to this documentation;
2. the skill file ``SDC_SKILL.md`` next to *manage.py* (``BASE_DIR``), written
   by ``sdc_teach``; if it does not exist, the ``SDC_SKILL.json`` files of the
   installed apps;
3. the files of ``SDC_AI_ADDITIONAL_SKILL_FILE``, e.g. a hand-written
   description of your workflows. Missing files are logged and skipped.

The prompt is built once per server process; restart the server after changing
the skill files. With ``DEBUG = True`` it is rebuilt for every connection, so
changes apply after a page reload.


What the assistant can do
-------------------------

The assistant acts through tools that run in the browser:

``navigate``
    Opens a view (``/~view~child~&key=value``), like a navigation link.
``read_page``
    Returns the URL, the title, a simplified HTML of the visible page (without
    scripts, styles, hidden elements, most attributes and the assistant itself)
    and the forms with their fields, labels, current values and options. Forms
    of inactive navigator views (hidden copies of a view opened before) are
    left out. A form
    with the attributes ``SdcModelName`` and ``SdcModelPK`` edits a record of
    that SdcModel (``SdcModelPK`` -1: a new record).
``fill_form``
    Enters values into inputs, textareas, selects, checkboxes and radios, and
    warns if the form is not visible. It never submits. In SdcModel forms it only fires ``input`` events, not the
    ``change`` event that makes ``sdc-model-form`` edit forms save themselves.
    The values are saved when the user saves the form (or changes another field
    of an auto-saving edit form).
``model_get``, ``model_load``
    Read one record by id, or up to 50 records with an optional filter (the
    server loads only these, using ``SdcQuerySet.load(query, {limit})``). They
    use the normal model WebSocket, so ``is_authorised`` and ``get_queryset`` of
    the model apply.

Password, hidden and file fields are never read or filled. A response may use
tools in up to five rounds; then the model has to answer.


The panel
---------

- The panel starts collapsed as a tab at the right edge; a click opens it, ⇆
  collapses it again.
- Drag the header to move it and the edges or corners to resize it; the browser
  remembers position and size. A double click on the header docks it at the
  right edge again.
- While an answer is running, a new question cannot be sent (the send button
  is disabled), so the assistant never acts on a page the user has moved on
  from.
- Answers are shown as formatted Markdown. Links to SDC views open in the
  ``sdc-navigator``. The model's text is never inserted as HTML.
- Enter sends, Shift+Enter adds a line break.


Privacy and security
--------------------

- The prompts, the skill file, the page content from ``read_page`` and the
  records from ``model_get``/``model_load`` are sent to the AI provider.
  Personal data that the user can see can therefore reach the provider; choose
  the provider accordingly.
- The assistant cannot exceed the user's rights: page actions run in the user's
  browser, model access goes through the model's permission checks.
- Keys entered by users stay in the server's memory for the open connection.
- The assistant's WebSocket only accepts connections from pages of your site:
  a browser's ``Origin`` header must match ``ALLOWED_HOSTS``, so other sites
  cannot use the assistant with a visitor's session. New projects check this
  for all SDC WebSockets (``AllowedHostsOriginValidator`` in ``asgi.py``).


The WebSocket protocol
----------------------

``SDCAiConsumer`` (route ``sdc_ws/ai``) speaks JSON. You only need this for your
own client.

Client to server:

``{"event": "prompt", "id": <id>, "prompt": "..."}``
    Ask; the conversation is kept per connection.
``{"event": "action_results", "id": <id>, "results": [{"tool_use_id", "content", "is_error"}]}``
    One result per action of an ``ai_actions`` message. Results for another
    request (e.g. of actions cancelled by a new prompt) are ignored.
``{"event": "set_config", "provider", "token", "base_url", "model", "effort", "max_tokens", "clear_token"}``
    The user's connection settings (own key only). Empty fields use the project
    settings; an empty ``token`` keeps the current key.
``{"event": "reset"}``
    Forget the conversation.

Server to client:

``{"type": "ai_config", ...}``
    The settings in use and what the user may change; after connecting and
    after ``set_config``. Never contains the key.
``{"type": "ai_delta", "id", "text"}``
    Streamed text of the answer.
``{"type": "ai_actions", "id", "text", "actions": [{"tool_use_id", "name", "input"}]}``
    Tools to run; the answer continues after ``action_results``.
``{"type": "ai_answer", "id", "text", "stop_reason"}``
    End of the answer.
``{"type": "error", "id", "msg", "header", "scope"}``
    ``scope`` is ``"settings"`` for rejected ``set_config`` values and, with the
    user's own key, for provider errors; ``"token"`` when an API key is needed. After ``ai_delta`` messages, an error
    means the partial answer is discarded.
