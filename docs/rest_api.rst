.. _sdc-rest-api-label:

REST API
========

Besides the WebSocket channel used by the client runtime, SDC exposes every SDC
model through a small JSON/HTTP API. The API is meant for scripts, mobile apps,
AI clients and other services that do not run the SDC client. It uses the same
model hooks (``is_authorised()`` / ``get_queryset()``) and the same forms
(``SdcMeta``) as the WebSocket channel, but authenticates with **API tokens**
instead of the Django session. The same tokens are used by the MCP endpoint
(:doc:`mcp`).

The code lives in *sdc_core/rest_api.py* (views), *sdc_core/api_tokens.py*
(tokens and privileges), *sdc_core/models.py* (``ApiToken``) and
*sdc_core/sdc_extentions/model_actions.py* (the model actions shared with MCP).

URLs
----

``sdc_init`` (see :ref:`sdc-init-core`) adds one route to your main
*urls.py*:

.. code-block:: python

   urlpatterns = [
       ...
       path('sdc_api/', include('sdc_core.api_urls')),
       ...
   ]

*./root_dir/<project>/urls.py*

``sdc_api/login/``
   Log in with username and password and receive a short-lived login token.

``sdc_api/tokens/``, ``sdc_api/tokens/current/``, ``sdc_api/tokens/<id>/``
   List, create and revoke the own API tokens.

``sdc_api/account/``
   Read and change the own user record.

``sdc_api/<model>/``
   Collection URL of a model (``AdcApi``). List and create.

``sdc_api/<model>/<id>/``
   Instance URL of a model (``AdcApi``). Read, update, partial update and delete.

``<model>`` is the class name of an SDC model in any letter case, so
``/sdc_api/book/``, ``/sdc_api/Book/`` and ``/sdc_api/BOOK/`` all address
``Book``. Only models that extend ``SdcModel`` are reachable; any other name
returns ``404``. The fixed routes come first: SDC models named ``Login``,
``Tokens`` or ``Account`` are not reachable through the REST API.

.. note::

   Projects created before 0.163.0 have three explicit routes
   (``sdc_api/login/``, ``sdc_api/<str:model>/<int:id>/``,
   ``sdc_api/<str:model>/``). They keep working for login and the models;
   replace them with the ``include`` above to get the token and account
   endpoints, and run ``python manage.py migrate`` for the ``ApiToken`` table.

All views are ``csrf_exempt``: they are called without a Django session and
need no CSRF token.

Authentication: API tokens
--------------------------

Every request (except the login) carries an API token:

.. code-block:: text

   Authorization: Bearer sdc_<random>

A token belongs to one user and has a name, privileges and usually an expiry
date. Only a SHA-256 hash of the token is stored: the token itself is shown
once, when it is created. Lists show its first characters (``prefix``) so you
can recognise it.

Users create tokens

- in the web app: ``<sdc-api-tokens>`` (the "API tokens" link of
  ``<sdc-user-nav-btn>``) lists, creates and revokes the own tokens,
- with ``POST /sdc_api/login/`` (username and password, a short-lived login
  token),
- through the API with a token that has ``account:tokens``
  (``POST /sdc_api/tokens/``),
- or an admin creates them with ``manage.py sdc_tokens create`` (see below).

A token stops working when it expires, when it is revoked, or when its user is
deactivated (``is_active = False``). Revoking a token also revokes every token
that was created with it. Revoked tokens stay in the list as history; admins
see and revoke all tokens in the Django admin.

Privileges
^^^^^^^^^^

The privileges of a token **narrow** what it may do; a token never has more
rights than its user. Every model action first checks the token's privileges,
then the model's own ``is_authorised()`` / ``get_queryset()`` for the user.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Privilege
     - Allows
   * - ``model:<Model>:read``
     - Read rows of the model (``GET``; action ``load``).
   * - ``model:<Model>:write``
     - Create and change rows (``POST``, ``PUT``, ``PATCH``; actions
       ``create`` and ``save``).
   * - ``model:<Model>:delete``
     - Delete rows (``DELETE``; action ``delete``).
   * - ``model:*:read`` / ``model:*:write`` / ``model:*:delete``
     - The same for every SDC model.
   * - ``account:read``
     - Read the own user record and the own token list.
   * - ``account:write``
     - Change the own profile. Password, e-mail and username can never be
       changed with a token.
   * - ``account:tokens``
     - Create tokens (with at most the own privileges, expiring no later) and
       revoke own tokens.

``write`` does not include ``read``, and ``delete`` does not include
``write``. The web app offers presets: *Read only* (``model:*:read``,
``account:read``), *Read & write* (also ``model:*:write``) and *Full access*
(all privileges).

A missing privilege is answered with ``403``, a JSON body that names it and the
header of RFC 6750:

.. code-block:: text

   HTTP/1.1 403 Forbidden
   WWW-Authenticate: Bearer error="insufficient_scope", scope="model:Book:write"

   {"success": false, "error": "The token lacks the privilege model:Book:write",
    "privilege": "model:Book:write"}

Errors of the authentication (``401``, JSON ``{"error": ...}``):
``Missing Authorization header``, ``Invalid Authorization header``,
``Invalid token`` (unknown token or inactive user), ``Expired token``,
``Revoked token``.

Login endpoint
^^^^^^^^^^^^^^

``POST /sdc_api/login/``
   Body: JSON with ``username`` and ``password``, optional ``name`` and
   ``privileges`` (a list; default: all privileges). Returns a token of kind
   ``login`` that is valid for ``SDC_API_TOKENS['login_lifetime_seconds']``:

   .. code-block:: json

      {
        "access_token": "sdc_4mZ0...",
        "token_type": "bearer",
        "token_id": "8f6c...",
        "expires_at": "2026-11-10T13:00:00Z",
        "privileges": ["account:read", "account:tokens", "account:write",
                       "model:*:delete", "model:*:read", "model:*:write"]
      }

   There is no refresh token: log in again, or use a personal token for
   long-running clients. Errors: ``400`` ``Missing credentials``,
   ``Invalid JSON`` or unknown privileges, ``401`` ``Invalid credentials``.

Token endpoints
^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 35 20 45

   * - Request
     - Privilege
     - Behaviour
   * - ``GET /sdc_api/tokens/``
     - ``account:read``
     - The user's tokens (also revoked and expired ones): ``id``, ``name``,
       ``kind``, ``prefix``, ``privileges``, ``created_at``, ``expires_at``,
       ``last_used_at``, ``revoked_at``, ``created_by_token``, ``is_valid``.
   * - ``POST /sdc_api/tokens/``
     - ``account:tokens``
     - Create a token: ``{"name", "privileges"?, "expires_at"?}``. Without
       ``privileges`` it gets those of the calling token; it may not get more.
       ``expires_at``: an ISO date-time, ``null`` for no expiry (only if
       ``max_lifetime_days`` is ``None``), or left out for the default
       lifetime. Answers ``201`` with ``{"token": "sdc_...", "data": {...}}`` —
       the only time the token is shown.
   * - ``GET /sdc_api/tokens/current/``
     - any
     - The calling token.
   * - ``GET /sdc_api/tokens/<id>/``
     - ``account:read``
     - One own token (``404`` for tokens of other users).
   * - ``DELETE /sdc_api/tokens/<id>/``
     - ``account:tokens``
     - Revoke an own token and the tokens created with it. A token may revoke
       itself.

Account endpoint
^^^^^^^^^^^^^^^^

``GET /sdc_api/account/`` (``account:read``)
   The own user record, serialized like a model row.

``PATCH /sdc_api/account/`` (``account:write``)
   Change the own profile with the user model's ``edit_form`` (partial
   update). Requests with ``password``, ``username``, ``email``,
   ``is_staff``, ``is_superuser``, ``groups`` or other protected fields, or
   with files, are refused with ``403``. The user model's own rules apply as
   well.

Settings
^^^^^^^^

``sdc_init`` writes the ``SDC_API_TOKENS`` setting:

.. code-block:: python

   SDC_API_TOKENS = {
       'max_lifetime_days': 365,
       'default_lifetime_days': 90,
       'login_lifetime_seconds': 3600,
       'accept_jwt': True,
   }

*./root_dir/<project>/settings.py*

``max_lifetime_days``
   Longest lifetime of a personal token. ``None``: tokens may never expire.

``default_lifetime_days``
   Lifetime of a personal token created without an expiry. ``None``: no expiry.

``login_lifetime_seconds``
   Lifetime of the tokens of ``/sdc_api/login/``.

``accept_jwt``
   Deprecated, see below.

Command line: ``sdc_tokens``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: sh

   python manage.py sdc_tokens list [--user jane] [--all]
   python manage.py sdc_tokens create --user jane --name "backup script" \
          --privileges "model:Book:read,account:read" [--days 30]
   python manage.py sdc_tokens revoke <prefix or id>

``--privileges`` takes a comma-separated list or a preset (``read``,
``read_write``, ``full``). Django options such as ``--settings`` go before the
sub-command (``sdc_tokens --settings x create ...``).

Using tokens in your own views
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``sdc_core.api_tokens.api_token_required`` authenticates the bearer token and
sets ``request.user``, ``request.api_grant`` (the privileges) and
``request.api_token``:

.. code-block:: python

   from django.http import JsonResponse
   from django.views.decorators.csrf import csrf_exempt
   from sdc_core import api_tokens

   @csrf_exempt
   @api_tokens.api_token_required
   def whoami(request):
       api_tokens.require_account(request.api_grant, api_tokens.ACCOUNT_READ)
       return JsonResponse({"username": request.user.username})

``require_account`` raises ``model_actions.MissingPrivilege``; answer it with
``api_tokens.insufficient_privilege_response(e)``. For model access use
``sdc_core.sdc_extentions.model_actions`` (``load``, ``get``, ``create``,
``update``, ``delete``) with ``grant=request.api_grant``.

Deprecated: JSON web tokens
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Versions up to 0.162 issued JSON web tokens (``JWT`` setting,
*sdc_core/jwt_utils.py*). For one release they are still accepted with the full
rights of their user, and ``GET /sdc_api/login/`` with a refresh JWT still
returns a (new) login token. Such responses carry ``Deprecation: true``. Set
``SDC_API_TOKENS['accept_jwt'] = False`` to refuse them now; they will be
removed. The MCP endpoint never accepts them.

Model endpoints (``AdcApi``)
----------------------------

``AdcApi`` checks the privilege of the token (``model:<Model>:read`` for
``GET``, ``:write`` for ``POST`` / ``PUT`` / ``PATCH``, ``:delete`` for
``DELETE``) and then authorizes the request with the model's own classmethods
``is_authorised(user, action, obj)`` and ``get_queryset(user, action, obj)``
(see :ref:`sdc-model-label`). ``user`` is the user of the token.

.. list-table::
   :header-rows: 1
   :widths: 22 25 53

   * - Request
     - Hooks
     - Behaviour
   * - ``GET /sdc_api/<model>/``
     - ``is_authorised(user, 'load', filter)``,
       ``get_queryset(user, 'load', filter)``
     - List all rows of ``get_queryset()`` that match the query-string filter.
   * - ``GET /sdc_api/<model>/<id>/``
     - ``is_authorised(user, 'load', {'pk': id})``,
       ``get_queryset(user, 'load', {'pk': id})``
     - Return one row. ``404`` if it does not exist or is not in
       ``get_queryset()``.
   * - ``POST /sdc_api/<model>/``
     - ``is_authorised(user, 'create', {})``
     - Create a row with ``SdcMeta.create_form``.
   * - ``PUT /sdc_api/<model>/<id>/``
     - ``is_authorised(user, 'save', {})``,
       ``get_queryset(user, 'save', {'pk': id})``
     - Update the row with ``SdcMeta.edit_form``. All required form fields must
       be sent.
   * - ``PATCH /sdc_api/<model>/<id>/``
     - same as ``PUT``
     - Partial update with ``SdcMeta.edit_form``. Form fields missing in the
       request are filled with the current values of the row.
   * - ``DELETE /sdc_api/<model>/<id>/``
     - ``is_authorised(user, 'delete', {'pk': id})``,
       ``get_queryset(user, 'delete', {'pk': id})``
     - Delete the row and answer ``{"success": true}``. ``404`` if it does not
       exist or is not in ``get_queryset()``.

Filtering lists
^^^^^^^^^^^^^^^

Query-string parameters of a list request become Django ``filter()`` keyword
arguments:

.. code-block:: sh

   curl -H "Authorization: Bearer $ACCESS" \
        "http://localhost:8000/sdc_api/book/?author=1&title__icontains=dune"

The part of each key before ``__`` must be a field the model exposes
(``SdcMeta.fields`` / ``SdcMeta.exclude``; ``pk`` and ``id`` are always
allowed). Other keys return ``403`` with the text
``Filtering on '<key>' is not allowed``. All values arrive as strings; if a
parameter is repeated, the last value is used.

Selecting fields
^^^^^^^^^^^^^^^^

``?_fields=title,author`` returns only these fields of each record (list and
detail requests); ``_fields`` is not a filter. Unknown or hidden field names
return ``400``.

Request bodies
^^^^^^^^^^^^^^

``POST``, ``PUT`` and ``PATCH`` accept three body formats:

- ``application/json``: a JSON object with the form fields (no files)
- ``application/x-www-form-urlencoded``
- ``multipart/form-data``, which is also the way to upload files

A JSON body that is not an object returns ``400``. For ``PATCH``, fields that are
missing in the body keep their current values.

Responses
^^^^^^^^^

List and detail responses wrap Django's serializer format (produced by
``SDCSerializer``). File fields are serialized as ``{"name": ..., "url": ...}``,
relations as primary keys:

.. code-block:: json

   {
     "success": true,
     "data": [
       {"model": "main_app.book", "pk": 1,
        "fields": {"title": "Dune", "author": 1}}
     ]
   }

For a detail request ``data`` is a single object instead of a list.

Create, update and partial update return the saved row in the same format as a
detail request, including its primary key:

.. code-block:: json

   {"success": true,
    "data": {"model": "main_app.book", "pk": 7,
             "fields": {"title": "Dune", "author": 1}}}

Validation errors return ``400`` with the form errors:

.. code-block:: json

   {"success": false, "errors": {"title": ["This field is required."]}}

``SdcMeta.fields`` and ``SdcMeta.exclude`` limit both the fields in responses
and the fields clients may filter on (see :ref:`sdc-model-label`).

Every successful create or update through the API also fires Django's
``post_save`` signal, so connected SDC clients receive the change as a live
update.

Error responses
^^^^^^^^^^^^^^^

``401``
   Missing, invalid, expired or revoked token (JSON ``{"error": ...}``, see
   above).

``403``
   The token lacks the privilege (JSON with ``privilege``, see above),
   ``is_authorised()`` returned ``False`` (empty body), or a filter key is not
   allowed (plain-text message).

``404``
   Unknown model name (Django's standard ``Http404`` page), or row not found or
   not part of ``get_queryset()`` (empty body).

``400``
   Form validation failed (``{"success": false, "errors": {...}}``) or the JSON
   body is not an object.

``405``
   ``POST`` to an instance URL, or ``PUT``, ``PATCH`` or ``DELETE`` to a
   collection URL (``{"success": false, "error": ...}``).

OpenAPI description (``sdc_open_api``)
--------------------------------------

Generate an OpenAPI 3.0.3 description of the API with:

.. code-block:: sh

   python manage.py sdc_open_api

The command writes *openapi.generated.yaml* into the current working directory
(run it next to *manage.py*). MCP clients can read the same description as the
resource ``sdc://openapi``. It contains:

- ``/sdc_api/login/``, ``/sdc_api/tokens/``, ``/sdc_api/tokens/current/``,
  ``/sdc_api/tokens/{token_id}/`` and ``/sdc_api/account/``
- for every SDC model ``/sdc_api/<model>/`` (``GET`` list with filter query
  parameters, ``POST`` create) and ``/sdc_api/<model>/{id}/`` (``GET``,
  ``PUT``, ``PATCH``, ``DELETE``); ``<model>`` is the lower-case class name
- the privilege every operation needs, in its summary
- the schemas ``<Model>`` (a serialized row: ``model``, ``pk``, ``fields``),
  ``<Model>Fields`` (the exposed fields, following ``SdcMeta.fields`` /
  ``exclude``), ``<Model>Create`` (from ``SdcMeta.create_form``),
  ``<Model>Edit`` (from ``SdcMeta.edit_form``), ``<Model>Patch``
  (``edit_form`` without required fields) and ``ApiToken``
- request bodies as JSON, form-encoded or multipart; forms with file fields
  only as ``multipart/form-data``
- the error responses (``400``, ``401``, ``403``, ``404``)
- a global ``BearerAuth`` (HTTP bearer, SDC API token) security scheme

A model without ``SdcMeta.create_form`` gets no ``POST``, a model without
``SdcMeta.edit_form`` no ``PUT`` / ``PATCH``. The file is plain YAML and valid
OpenAPI 3.0.

To browse or try the API, load the file into Swagger UI or any OpenAPI tool,
for example:

.. code-block:: sh

   docker run -p 8080:8080 -e SWAGGER_JSON=/api/openapi.generated.yaml \
          -v "$PWD":/api swaggerapi/swagger-ui

Authorize with an API token. Requests from Swagger UI to your Django server are
cross-origin, so they may need CORS headers on the server.


Example with curl
-----------------

The example assumes an SDC model ``Author`` with the fields ``name`` and
``age``.

.. code-block:: sh

   # 1. Log in (or create a personal token under "API tokens" in the web app)
   curl -s -X POST http://localhost:8000/sdc_api/login/ \
        -H "Content-Type: application/json" \
        -d '{"username": "admin", "password": "secret"}'
   # {"access_token": "sdc_...", "token_type": "bearer", "token_id": "...", ...}

   TOKEN=<access_token>

   # 2. List authors, optionally filtered
   curl -s http://localhost:8000/sdc_api/author/?age=22 \
        -H "Authorization: Bearer $TOKEN"

   # 3. Create an author (form data)
   curl -s -X POST http://localhost:8000/sdc_api/author/ \
        -H "Authorization: Bearer $TOKEN" \
        -d "name=Ada" -d "age=36"

   # 4. Change a single field
   curl -s -X PATCH http://localhost:8000/sdc_api/author/3/ \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"age": 38}'

   # 5. Create a read-only token for a script (needs account:tokens)
   curl -s -X POST http://localhost:8000/sdc_api/tokens/ \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"name": "report script", "privileges": ["model:Author:read"]}'

   # 6. Revoke the login token when you are done
   curl -s -X DELETE http://localhost:8000/sdc_api/tokens/<token_id>/ \
        -H "Authorization: Bearer $TOKEN"
