.. _sdc-rest-api-label:

REST API
========

Besides the WebSocket channel used by the client runtime, SDC exposes every SDC
model through a small JSON/HTTP API. The API is meant for scripts, mobile apps
and other services that do not run the SDC client. It uses the same model hooks
(``is_authorised()`` / ``get_queryset()``) and the same forms (``SdcMeta``) as
the WebSocket channel, but authenticates with JSON Web Tokens (JWT) instead of
the Django session.

The code lives in *sdc_core/rest_api.py* (views) and *sdc_core/jwt_utils.py*
(tokens).

URLs
----

``sdc_init`` (see :ref:`sdc-init-core`) adds these routes to your main
*urls.py*:

.. code-block:: python

   from sdc_core.rest_api import AdcApi, get_api_token

   urlpatterns = [
       ...
       path('sdc_api/<str:model>/<int:id>/', AdcApi.as_view()),
       path('sdc_api/<str:model>/', AdcApi.as_view()),
       path('sdc_api/login/', get_api_token),
       ...
   ]

*./root_dir/<project>/urls.py*

``sdc_api/login/``
   Token endpoint (``get_api_token``). Log in and refresh tokens.

``sdc_api/<model>/``
   Collection URL of a model (``AdcApi``). List and create.

``sdc_api/<model>/<id>/``
   Instance URL of a model (``AdcApi``). Read, update and partial update.

``<model>`` is the class name of an SDC model in any letter case, so
``/sdc_api/book/``, ``/sdc_api/Book/`` and ``/sdc_api/BOOK/`` all address
``Book``. Only
models that extend ``SdcModel`` are reachable; any other name returns ``404``.

.. note::

   The login route must come before the model routes, otherwise
   ``/sdc_api/login/`` is handled as a model named ``login`` and every login
   fails with ``401 {"error": "Missing Authorization header"}``. ``sdc_init``
   writes them in the right order (projects created with versions before
   0.159.0 have them the other way round):

   .. code-block:: python

      urlpatterns = [
          path('sdc_api/login/', get_api_token),
          path('sdc_api/<str:model>/<int:id>/', AdcApi.as_view()),
          path('sdc_api/<str:model>/', AdcApi.as_view()),
          ...
      ]

Both views are ``csrf_exempt``: they are called without a Django session and
need no CSRF token.

Authentication
--------------

Token endpoint
^^^^^^^^^^^^^^

``POST /sdc_api/login/``
   Log in. The body must be JSON with ``username`` and ``password``. The
   credentials are checked with Django's ``authenticate()``, ``last_login`` of
   the user is updated, and a new token pair is returned:

   .. code-block:: json

      {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
        "token_type": "bearer"
      }

``GET /sdc_api/login/``
   Refresh. Send the **refresh** token in the ``Authorization`` header
   (``Authorization: Bearer <refresh_token>``). The response is a new token pair
   in the same format.

Error responses of the token endpoint (all JSON ``{"error": "..."}``):

- ``400`` ``Missing credentials`` (username or password empty) or
  ``Invalid JSON``
- ``401`` ``Invalid credentials``, or for a refresh ``Expired token``,
  ``Invalid token``, ``User not found``, ``Missing Authorization header``,
  ``Invalid Authorization header``
- ``405`` ``POST required`` for methods other than ``GET`` and ``POST``
- ``500`` ``Internal server error`` (the exception text when ``DEBUG`` is on)

Tokens
^^^^^^

Both tokens are signed JWTs with the claims ``user_id``, ``username``,
``iat``, ``exp`` and ``type`` (``auth`` or ``refresh``). The type is checked:
an access token cannot be used for a refresh, and a refresh token is not
accepted by the model endpoints.

Access token
   Valid for ``JWT['exp_delta_seconds']`` seconds (3600 in the generated
   settings, i.e. one hour).

Refresh token
   Valid for 20 × ``exp_delta_seconds`` (20 hours with the default). The factor
   is fixed in *sdc_core/jwt_utils.py*. A refresh token is additionally bound to
   the user's ``last_login``: it is only accepted if its ``iat`` lies within 10
   seconds of ``last_login``. Because every login **and** every refresh updates
   ``last_login``, only the most recently issued refresh token is valid. A
   refresh (or a new login, also through the web login page) invalidates all
   older refresh tokens. Access tokens stay valid until they expire.

Tokens of an inactive user (``is_active = False``) are rejected: deactivating
a user blocks new logins, already issued access tokens and refreshes.

Settings
^^^^^^^^

``sdc_init`` writes the ``JWT`` setting:

.. code-block:: python

   JWT = {'secret': SECRET_KEY, 'algorithm': 'HS256' , 'exp_delta_seconds': 3600}

*./root_dir/<project>/settings.py*

``secret``
   Key used to sign and verify all tokens. Defaults to ``SECRET_KEY``.

``algorithm``
   PyJWT signing algorithm. Default ``HS256``.

``exp_delta_seconds``
   Lifetime of the access token in seconds. The refresh token lives 20 times as
   long.

The same ``secret`` and ``algorithm`` also sign the e-mail confirmation and
password reset links of ``sdc_user`` (see :ref:`sdc-user-label`).

Authorization header and ``jwt_required``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Every request to a model endpoint must carry the access token:

.. code-block:: text

   Authorization: Bearer <access_token>

The check is done by the decorator ``sdc_core.jwt_utils.jwt_required``. It
verifies the token, loads the user and sets ``request.user``. On failure it
returns ``401`` with one of these JSON errors: ``Missing Authorization header``,
``Invalid Authorization header``, ``Expired token``, ``Invalid token``,
``User not found``.

You can use the decorator for your own endpoints:

.. code-block:: python

   from django.http import JsonResponse
   from django.views.decorators.csrf import csrf_exempt
   from sdc_core.jwt_utils import jwt_required

   @csrf_exempt
   @jwt_required
   def whoami(request):
       return JsonResponse({"username": request.user.username})

For class-based views use
``@method_decorator(jwt_required, name="dispatch")``, as ``AdcApi`` does.

Model endpoints (``AdcApi``)
----------------------------

``AdcApi`` authorizes every request with the model's own classmethods
``is_authorised(user, action, obj)`` and ``get_queryset(user, action, obj)``
(see :ref:`sdc-model-label`). ``user`` is the user of the access token.

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
     - none
     - Not implemented. Always ``501`` with
       ``{"success": false, "error": "Delete is not supported"}``.

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

Request bodies
^^^^^^^^^^^^^^

The model endpoints read form data, not JSON:

- ``POST`` reads ``request.POST`` / ``request.FILES``, so send
  ``application/x-www-form-urlencoded`` or ``multipart/form-data``. Files can
  only be uploaded this way.
- ``PUT`` and ``PATCH`` parse the raw body as
  ``application/x-www-form-urlencoded``. Multipart bodies and files are not
  supported for them.

A JSON body is not parsed; the form then sees no data and returns validation
errors.

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
   Missing, invalid or expired access token (JSON ``{"error": ...}``, see above).

``403``
   ``is_authorised()`` returned ``False`` (empty body), or a filter key is not
   allowed (plain-text message).

``404``
   Unknown model name (Django's standard ``Http404`` page), row not found or not
   part of ``get_queryset()`` (empty body), or ``POST`` to an instance URL
   (``Cannot create with id``).

``400``
   Form validation failed (``{"success": false, "errors": {...}}``).

``501``
   ``DELETE``.

.. note::

   ``PUT``, ``PATCH`` and ``DELETE`` on a collection URL (without id) end in a
   server error (``500``), because these handlers require the ``id`` URL
   argument.

OpenAPI description (``sdc_open_api``)
--------------------------------------

Generate an OpenAPI 3.0.3 description of the API with:

.. code-block:: sh

   python manage.py sdc_open_api

The command writes *openapi.generated.yaml* into the current working directory
(run it next to *manage.py*). It contains:

- ``/sdc_api/login/`` with ``POST`` (login, no security) and ``GET`` (refresh)
- for every SDC model ``/sdc_api/<model>/`` (``GET`` list, ``POST`` create) and
  ``/sdc_api/<model>/{id}/`` (``GET``, ``PUT``, ``PATCH``); ``<model>`` is the
  lower-case class name
- the schemas ``<Model>`` (from the model fields), ``<Model>Create`` (from
  ``SdcMeta.create_form``), ``<Model>Edit`` (from ``SdcMeta.edit_form``) and
  ``<Model>Patch`` (``edit_form`` without required fields)
- a global ``BearerAuth`` (HTTP bearer, JWT) security scheme

Every SDC model must define **both** ``SdcMeta.edit_form`` and
``SdcMeta.create_form``, because the command imports them for every model. A
model without them makes the command fail.

To browse or try the API, load the file into Swagger UI or any OpenAPI tool,
for example:

.. code-block:: sh

   docker run -p 8080:8080 -e SWAGGER_JSON=/api/openapi.generated.yaml \
          -v "$PWD":/api swaggerapi/swagger-ui

Authorize with the ``access_token`` from ``/sdc_api/login/``. Requests from
Swagger UI to your Django server are cross-origin, so they may need CORS
headers on the server.

.. note::

   The generated file is a starting point and differs from the real API in some
   places:

   - request bodies of forms without file fields are declared as
     ``application/json``, but the endpoints only read form-encoded data
     (see `Request bodies`_)
   - the model schemas describe a flat object (``id`` plus fields), while the
     responses use the ``{"model", "pk", "fields"}`` format
   - ``POST`` is documented as ``201``, the endpoint answers ``200``
   - ``DELETE`` is not listed
   - ``DateTimeField`` values are declared with ``format: date``
   - safe strings used as help texts (e.g. Django's password validator
     help) are written with a Python-specific YAML tag
     (``!!python/object/new:django.utils.safestring.SafeString``), which some
     YAML parsers reject; remove these tags by hand if your tool fails to load
     the file

Example with curl
-----------------

The example assumes an SDC model ``Author`` with the fields ``name`` and
``age``, and the login route moved above the model routes (see the warning in
`URLs`_).

.. code-block:: sh

   # 1. Log in (JSON body)
   curl -s -X POST http://localhost:8000/sdc_api/login/ \
        -H "Content-Type: application/json" \
        -d '{"username": "admin", "password": "secret"}'
   # {"access_token": "...", "refresh_token": "...", "token_type": "bearer"}

   ACCESS=<access_token>
   REFRESH=<refresh_token>

   # 2. List authors, optionally filtered
   curl -s http://localhost:8000/sdc_api/author/?age=22 \
        -H "Authorization: Bearer $ACCESS"

   # 3. Create an author (form data)
   curl -s -X POST http://localhost:8000/sdc_api/author/ \
        -H "Authorization: Bearer $ACCESS" \
        -d "name=Ada" -d "age=36"
   # {"success": true, "data": {"name": "Ada", "age": 36}}

   # 4. Read one author
   curl -s http://localhost:8000/sdc_api/author/3/ \
        -H "Authorization: Bearer $ACCESS"

   # 5. Replace all fields
   curl -s -X PUT http://localhost:8000/sdc_api/author/3/ \
        -H "Authorization: Bearer $ACCESS" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        --data "name=Ada Lovelace&age=37"

   # 6. Change a single field
   curl -s -X PATCH http://localhost:8000/sdc_api/author/3/ \
        -H "Authorization: Bearer $ACCESS" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        --data "age=38"

   # 7. Get a new token pair with the refresh token
   curl -s http://localhost:8000/sdc_api/login/ \
        -H "Authorization: Bearer $REFRESH"
