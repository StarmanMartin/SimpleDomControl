.. _sdc-mcp-label:

MCP endpoint
============

SDC projects can offer an `MCP <https://modelcontextprotocol.io>`_ server, so
that AI clients such as Claude Code, Claude Desktop or Cursor can read and,
when allowed, change the data of the application. The client acts with the
rights of a user, narrowed by the privileges of an API token
(:doc:`rest_api`), and gets the knowledge that ``sdc_teach`` wrote about the
application (:doc:`teaching`).

The endpoint is ``/sdc_mcp/``. It is off until you enable it. The code lives in
*sdc_core/mcp/*.

Set up
------

1. Projects created with 0.163.0 or later have the route; older projects add
   it to their main *urls.py*:

   .. code-block:: python

      urlpatterns = [
          ...
          path('sdc_mcp/', include('sdc_core.mcp.urls')),
          ...
      ]

2. Enable it in *settings.py* and run ``python manage.py migrate`` (for the
   API tokens):

   .. code-block:: python

      SDC_MCP = {
          'enabled': True,
          'models': '__all__',
          'max_records': 50,
      }

3. Create an API token: in the web app under "API tokens"
   (``<sdc-api-tokens>``), or with the command below. Give it only the
   privileges the client needs — *Read only* is a good start.

4. Connect the client. ``sdc_mcp_config`` prints the commands for your
   project:

   .. code-block:: sh

      python manage.py sdc_mcp_config --url https://myapp.example.org
      # with a new token for jane (shown once):
      python manage.py sdc_mcp_config --user jane --privileges read

   For Claude Code:

   .. code-block:: sh

      claude mcp add --transport http myapp https://myapp.example.org/sdc_mcp/ \
             --header "Authorization: Bearer sdc_..."

   Or an *.mcp.json* entry that reads the token from the environment, so it
   stays out of the repository:

   .. code-block:: json

      {
        "mcpServers": {
          "myapp": {
            "type": "http",
            "url": "https://myapp.example.org/sdc_mcp/",
            "headers": {"Authorization": "Bearer ${SDC_MCP_TOKEN}"}
          }
        }
      }

Settings
--------

``enabled``
   ``False`` (default): the endpoint answers ``404``.

``models``
   ``'__all__'`` or a list of SDC model names that MCP clients may use at
   all. A model with ``SdcMeta.mcp = False`` is never exposed:

   .. code-block:: python

      class Salary(models.Model, SdcModel):
          class SdcMeta:
              mcp = False

``max_records``
   The most records ``model_load`` returns per call (default 50).

``name``
   The server name shown to clients (default: the name of the project
   directory).

``instructions``
   What of the ``sdc_teach`` knowledge goes into the server instructions:
   ``'models'`` (default) only the exposed data models of the index — views
   and the URL guide matter only for the browser assistant —, ``'index'`` the
   whole index, ``'none'`` nothing. Details are always available through
   ``describe`` and the resources.

Tools
-----

A client only sees the tools its token allows, and only for the exposed
models. Every call runs through the same code as the REST API: the token's
privileges are checked first, then the model's ``is_authorised()`` and
``get_queryset()`` for the user.

.. list-table::
   :header-rows: 1
   :widths: 28 22 50

   * - Tool
     - Listed when the token has
     - Does
   * - ``model_load``
     - ``model:<Model>:read`` for any model
     - Load records of a model, with Django field lookups as ``filter``
       (``{"age__gte": 18}``), ``limit`` and ``fields`` (only these fields of
       each record). Returns ``records``, ``total`` and ``truncated``.
   * - ``model_get``
     - ``model:<Model>:read`` for any model
     - One record by its id (optionally only ``fields``).
   * - ``describe``
     - (always, if there is skill data)
     - The documentation of a view, controller or model from
       *SDC_SKILL.data.json* (``sdc_teach``).
   * - ``account_get``
     - ``account:read``
     - The own user record.
   * - ``<model>_create``
     - ``model:<Model>:write``
     - Create a record with the model's ``create_form``. Models whose create
       form needs a file get no create tool.
   * - ``<model>_update``
     - ``model:<Model>:write``
     - Change fields of a record with the ``edit_form``; fields that are left
       out keep their values.
   * - ``<model>_delete``
     - ``model:<Model>:delete``
     - Delete a record.
   * - ``account_update``
     - ``account:write``
     - Change the own profile (never password, e-mail or username).

``<model>`` is the model name in snake case: ``BookContent`` →
``book_content_create``. The input schemas of the write tools are the same as
the ``<Model>Create`` / ``<Model>Patch`` schemas of the OpenAPI description.
The forms validate the values; their errors go back to the client per field, so
the AI model can correct them. File fields cannot be set over MCP.

All tools carry MCP annotations: the read tools are ``readOnlyHint``, update
and delete tools ``destructiveHint``, so clients ask the user before they run
them. The server instructions also ask the model to confirm changes with the
user.

Resources and instructions
--------------------------

The server instructions describe the application; with skill data they contain
the index of ``sdc_teach`` (one line per view, controller and model), and the
details come from ``describe``.

``sdc://skill``
   The skill file (*SDC_SKILL.assistant.md* or *SDC_SKILL.md*, see
   ``SDC_AI_SKILL_FILE``).

``sdc://skill/<app>``
   The *SDC_SKILL.json* of each installed app.

``sdc://openapi``
   The OpenAPI description of the REST API (``sdc_open_api``).

Run ``python manage.py sdc_teach`` after changing views or models, so the
knowledge stays current.

Protocol and security
---------------------

- Transport: MCP *Streamable HTTP*, stateless. Each ``POST`` carries one
  JSON-RPC message; requests are answered with ``application/json``,
  notifications with ``202``. There is no server-sent event stream (``GET``
  and ``DELETE`` answer ``405``) and no session. Protocol versions
  2025-03-26, 2025-06-18 and 2025-11-25; the newest is offered when a client
  asks for another one.
- Authentication: an API token as bearer token, on every request. Missing,
  unknown, expired or revoked tokens get ``401``. The deprecated JSON web
  tokens are not accepted. OAuth is not supported yet, so clients that only
  connect with OAuth cannot use the endpoint.
- Browser pages of other sites are refused: a request with an ``Origin`` header
  must match ``ALLOWED_HOSTS`` (protection against DNS rebinding). Programs
  send no ``Origin`` and are not affected.
- Revoke a token in the web app or with ``manage.py sdc_tokens revoke`` as soon
  as a client no longer needs it.
