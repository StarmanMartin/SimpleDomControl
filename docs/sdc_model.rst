.. _sdc-model-label:

SDC Models
==========

SDC extends Django models so they can also be used from the browser through the
client runtime. The server remains authoritative, but the client gets typed
model objects, queryset-style access, server-rendered forms and views, and live
updates over WebSockets.

This page covers, in order: the server-side model (metadata, rendering, search,
serialization), authorization, client querysets, ``SdcModel`` instances, forms
and synchronization, field types, live updates and the WebSocket protocol.

Creating a model
----------------

Generate a model scaffold with:

.. code-block:: sh

   python manage.py sdc_new_model -a <django_app_name> -m <ModelName>

Use CamelCase for the model name.

The command generates:

- a Django model class with a nested ``SearchForm``, an ``SdcMeta`` class and a
  ``render()`` classmethod that applies the search form to list views
- a form class
- default list/detail templates in ``<app>/templates/<app>/models/<Model>/``,
  linked into ``<app>/Assets/src/<app>/models/<Model>/``
- ``is_authorised()`` and ``get_queryset()`` classmethods

.. warning::

   The generated ``is_authorised()`` returns ``False``, so a new model is closed
   to every client action until you edit it.

A model becomes an SDC model by mixing in
``sdc_core.sdc_extentions.models.SdcModel``:

.. code-block:: python

   from django.db import models
   from sdc_core.sdc_extentions.models import SdcModel

   class Book(models.Model, SdcModel):
       class SdcMeta:
           edit_form = "main_test.forms.BookForm"
           create_form = "main_test.forms.BookForm"
           html_list_template = "main_test/models/Book/Book_list.html"
           html_detail_template = "main_test/models/Book/Book_details.html"

       title = models.CharField(max_length=255)
       author = models.ForeignKey(Author, on_delete=models.CASCADE)

       @classmethod
       def is_authorised(cls, user, action, obj):
           return user.is_authenticated

       @classmethod
       def get_queryset(cls, user, action, obj):
           return cls.objects.all()

Server model metadata
---------------------

Generated models use SDC metadata to define the forms and templates used by the
runtime. These templates are not only presentation helpers. They are part of the
model workflow used by the client for list rendering, detail rendering, and form
submission.

``SdcMeta`` keys
~~~~~~~~~~~~~~~~

``edit_form``
   Form used by ``edit_form`` (render) and ``save`` requests. Default ``None``;
   requesting it while unset fails with ``NotImplementedError``.

``create_form``
   Form used by ``create_form`` (render) and ``create`` requests. Default
   ``None``.

``html_list_template``
   Template used by ``listView()``. Default ``None``; a list view request fails
   while it is unset.

``html_detail_template``
   Template used by ``detailView()``. Default ``None``.

``html_form_template``
   Template that renders every model form (edit, create and named forms, and the
   form returned after a save/create). Default: ``settings.MODEL_FORM_TEMPLATE``
   if that setting exists, otherwise ``"elements/form.html"``. The default is
   read once when ``sdc_core.sdc_extentions.models`` is imported.

``fields``
   Whitelist of field names. Default ``"__all__"``; ``"*"`` means the same.

``exclude``
   Blacklist of field names. Default ``None``.

``on_disconnected(qs)``
   Optional hook called when a model WebSocket closes. ``qs`` is the result of
   loading the model with the action ``disconnect`` (``get_queryset()`` plus the
   connection's last filter). It is called as ``SdcMeta.on_disconnected(qs)``,
   so define it as a ``staticmethod`` or ``classmethod``.

Any other attribute
   Extra attributes act as *named forms* or *named views*, looked up by name:

   - a named form is requested with ``model.namedForm({formName: "<attr>"})``
     and saved with ``model.save({formName: "<attr>"})``. The attribute holds a
     form, like ``edit_form``.
   - a named view is requested with ``queryset.view({viewName: "<attr>"})``.
     The attribute holds a template name.

Form values (``edit_form``, ``create_form``, named forms) can be a dotted
import string (``"app.forms.BookForm"``) or the form class itself.

.. note::

   When a form is **rendered** (``edit_form``, ``create_form``,
   ``named_form`` requests), a callable value is first called with ``{}`` and
   its result is used. A form class is callable, so a class given directly is
   instantiated there and rendering then fails. For rendering, use the import
   string (or a callable that returns the import string or class). ``save`` and
   ``create`` accept both forms directly.

``fields`` and ``exclude`` are used in three places: the filter keys a client
may use (see :ref:`sdc-model-filter-sanitising`), the fields that
``sdc_make_model_js`` puts into the generated JavaScript class, and the
serializer output sent to clients (but see the warning below). The rules are:

- ``fields`` is ``None``/``"__all__"``/``"*"`` and ``exclude`` is ``None``: all
  fields.
- ``fields`` is an iterable and ``exclude`` is ``None``: only those fields.
- ``fields`` is ``None`` and ``exclude`` is an iterable: all except those.
- anything else (both set) raises an exception: the two are mutually exclusive.

.. note::

   ``fields`` defaults to ``"__all__"``, and ``"__all__"`` short-circuits the
   check before ``exclude`` is looked at. Setting only ``exclude`` therefore has
   no effect; set ``fields = None`` together with ``exclude``.

.. warning::

   In the serializer output the rules are applied to the top-level keys of each
   serialized object (``model``, ``pk``, ``fields``), not to the model fields.
   ``exclude`` therefore removes no field from the data sent to clients, and a
   ``fields`` list produces empty objects. Do not rely on ``fields`` /
   ``exclude`` to hide data from clients; restrict access with
   ``is_authorised()`` / ``get_queryset()`` instead.

Ways to declare the metadata
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``SdcModel.__init_subclass__`` normalizes the metadata of every subclass:

- A nested class named ``_SdcMeta`` is used as ``SdcMeta`` (the example app
  uses this spelling).
- If the class does not define ``SdcMeta`` itself, an empty ``SdcMeta`` is
  created.
- Every missing default key (``fields``, ``exclude``, ``edit_form``,
  ``create_form``, ``html_list_template``, ``html_detail_template``,
  ``html_form_template``) is taken from a plain class attribute of the same name
  if there is one, otherwise from the default.

So these two declarations are equivalent:

.. code-block:: python

   class Author(models.Model, SdcModel):
       edit_form = "main_test.forms.AuthorForm"
       html_list_template = "main_test/models/Author/Author_list.html"

   class Author(models.Model, SdcModel):
       class SdcMeta:
           edit_form = "main_test.forms.AuthorForm"
           html_list_template = "main_test/models/Author/Author_list.html"

Only the default keys are copied from class attributes. Named forms, named views
and ``on_disconnected`` must be defined inside ``SdcMeta``/``_SdcMeta``.

Rendering and template context
------------------------------

All model HTML goes through one classmethod, which you can override:

``render(cls, template_name, context=None, request=None, using=None)``
   Default: ``render_to_string(template_name, context, request, using)``. The
   consumer calls it as ``render(template_name, context)``, so ``request`` is
   always ``None``.

The context is built as ``scope | args | view_context``:

- ``scope``: the Channels scope of the connection (``user``, ``session``,
  ``url_route``, ...), plus ``request`` (the raw incoming message) and
  ``event_type``.
- ``args``: the ``args`` of the client message, e.g. ``model_query``, ``pk``,
  ``view_name``, ``form_name`` and ``template_context``. The client's
  ``templateContext`` option therefore arrives as the variable
  ``template_context``.
- the view-specific keys:

.. list-table::
   :header-rows: 1

   * - Request
     - Template
     - View-specific context
   * - ``listView()``
     - ``html_list_template``
     - ``instances`` (the loaded queryset), ``filter`` (the client's
       ``searchValues``)
   * - ``view({viewName})``
     - ``SdcMeta.<viewName>``
     - ``instances``
   * - ``detailView()``
     - ``html_detail_template``
     - ``instance``
   * - ``form()`` / ``namedForm()`` / save / create
     - ``html_form_template``
     - ``instance``, ``form`` (after save/create: the bound, validated form)

The generated ``render()`` hooks the search form into the list view:

.. code-block:: python

   @classmethod
   def render(cls, template_name, context=None, request=None, using=None):
       if template_name == cls.SdcMeta.html_list_template:
           sf = cls.SearchForm(data=context.get("filter", {}))
           context = context | handle_search_form(context["instances"], sf, range=10)
       return render_to_string(template_name=template_name, context=context,
                               request=request, using=using)

Search forms
------------

``sdc_core.sdc_extentions.forms.AbstractSearchForm`` is a Django form to be used
together with ``handle_search_form``. ``SdcModel`` ships a nested default
``SearchForm`` (search and order by ``id``). Subclass it to customize:

.. code-block:: python

   class BookSearchForm(AbstractSearchForm):
       CHOICES = (("title", "Title"), ("author__name", "Author"))
       PLACEHOLDER = "Book"
       DEFAULT_CHOICES = CHOICES[0][0]
       SEARCH_FIELDS = ("title", "author__name")

Class attributes:

``CHOICES``
   Tuple of ``(value, label)`` pairs for the ``order_by`` select. If empty, the
   ``order_by`` field is removed and results are not ordered.

``DEFAULT_CHOICES``
   Initial ``order_by`` value, and the ordering used when the form is invalid.

``SEARCH_FIELDS``
   Field lookups searched with ``icontains``.

``PLACEHOLDER``
   Placeholder of the search input. Default ``"Search"`` (translated).

``NO_RESULTS_ON_EMPTY_SEARCH``
   If ``True``, an empty search returns no instances. Default ``False``.

Form fields: ``search`` (text, max. 100 characters), ``order_by`` (select),
``range_start`` (hidden integer, default ``0``) and ``_method`` (hidden,
required, initial ``"search"``). The HTML ids are prefixed with the form class
name. An empty data dict gives an unbound form.

``handle_search_form(query_set, search_form, filter_dict=None, range=0)``
   Applies the form to ``query_set`` and returns a context dict:

   - the search text is split on spaces; every word must match at least one of
     ``SEARCH_FIELDS`` (``icontains``, results made ``distinct()``)
   - ``filter_dict``, if given, is applied with ``filter(**filter_dict)`` first
   - the result is ordered by ``order_by`` when ``CHOICES`` is not empty

   Returned keys:

   ``instances``
      The resulting queryset (sliced if ``range > 0``).
   ``total_count``
      Number of matches before slicing.
   ``search_form``
      The form, for rendering.
   ``range``
      Only if ``range > 0``: ``[first, last]``, 1-based, of the current slice.
      The slice starts at ``range_start``; if that is past the end it starts at
      ``max(total_count - 2, 0)``.
   ``range_size``
      Only if ``range > 0``: the ``range`` argument.

.. note::

   If the submitted data is invalid, the search is ignored and all rows are
   returned ordered by ``DEFAULT_CHOICES``. ``_method`` is required, so send the
   values of the complete rendered search form (including the hidden fields) as
   ``searchValues``. A valid form with an empty ``order_by`` passes ``""`` to
   ``order_by()``, which Django rejects. ``AbstractSearchForm(data=None)`` raises
   because ``len(None)`` is evaluated; pass ``{}`` for an empty form.

Serialization
-------------

Instances are serialized with ``SDCSerializer``, based on Django's JSON
serializer (``[{"model": ..., "pk": ..., "fields": {...}}]``):

- ``fields``/``exclude`` from ``SdcMeta`` are passed to the output filter, but
  applied to the wrong level (see the warning in `Server model metadata`_), so
  in practice all fields are sent.
- A ``FileField`` becomes ``{"name": <basename>, "url": <file.url>}``, or
  ``null`` if empty.
- Foreign keys are the related primary key; many-to-many fields are a list of
  primary keys. Reverse relations are not included.

Authorization
-------------

Models are responsible for authorizing their own SDC actions. Two classmethods
work together:

``is_authorised(cls, user, action, obj)``
   Returns whether ``user`` may perform ``action``. ``action`` is one of:
   ``connect``, ``load``, ``list_view``, ``detail_view``, ``named_view``,
   ``edit_form``, ``named_form``, ``create_form``, ``save``, ``create``,
   ``upload``, ``delete``. ``obj`` is the filter dict (``model_query``) sent by
   the client queryset, not a model instance. Form requests
   (``edit_form``, ``create_form``, ``named_form``) send no ``model_query``, so
   ``obj`` is ``{}`` for them. For ``list_view`` it still contains the
   ``__search_values`` key. It is checked for every message, including every
   upload chunk.

``get_queryset(cls, user, action, obj)``
   Returns the rows this user may see or operate on for the given action. It is
   also called with the action ``disconnect`` when a queryset connection
   closes.

.. warning::

   **Deny-by-default.** ``is_authorised()`` and ``get_queryset()`` have **no usable
   defaults** — ``is_authorised`` returns ``False`` and ``get_queryset`` raises. A
   model that does not override **both** is fully closed and every SDC action on it
   is forbidden. This is deliberate; always provide both.

.. code-block:: python

   @classmethod
   def is_authorised(cls, user, action, obj):
       return user.is_authenticated

   @classmethod
   def get_queryset(cls, user, action, obj):
       return cls.objects.all()

A denied request is answered with an error message (``"403 Not allowed!"``);
any other exception is answered with the exception details when ``DEBUG`` is on,
otherwise with ``"Something went wrong!"``.

How rows are loaded
~~~~~~~~~~~~~~~~~~~

Every server action that needs rows (load, views, forms, save, delete, live
updates) loads them the same way:

1. ``qs = get_queryset(user, action, model_query)``
2. ``result = data_load(user, qs, model_query)``; if the result is not ``None``
   it is used as is and the remaining steps are skipped
3. ``qs.filter(**sanitize_filter_query(model, model_query))``

Single-instance actions (edit/named form, save, detail view, delete) then call
``.get(pk=...)`` on that result, so a row outside ``get_queryset()`` or outside
the filter cannot be edited, viewed or deleted.

``data_load(cls, user, action, obj)``
   Optional classmethod hook, default returns ``None``. Although the declared
   parameters are ``(user, action, obj)``, the consumer calls it as
   ``data_load(user, queryset, model_query)``: the second argument is the
   queryset returned by ``get_queryset()``, not the action. If it returns
   something other than ``None``, that value replaces the loaded rows: the
   client filter is neither sanitised nor applied, and the list of loaded ids
   used for live updates is not updated. Return a ``QuerySet``, since
   single-instance actions call ``.get(pk=...)`` on it.

.. _sdc-model-filter-sanitising:

Filter sanitising
~~~~~~~~~~~~~~~~~

The client decides the filter (``model_query``). Before it is passed to
``filter()``, ``sanitize_filter_query()`` checks every key: the part before the
first ``__`` must be in ``get_filterable_fields(model)``, which is the model's
field names (``_meta.get_fields()``) restricted by ``SdcMeta.fields``/
``exclude``, plus ``pk`` and ``id``. Lookups on allowed fields, such as
``title__icontains`` or ``author__name``, are accepted.

A rejected key raises ``PermissionDenied``, and the request is answered with the
``"403 Not allowed!"`` error. For live ``on_create`` checks the error is
swallowed and the event is simply not sent.

The ``scope`` property
~~~~~~~~~~~~~~~~~~~~~~

The instance that a create/edit/named form, a save, a create, a detail view or
a delete works on gets ``instance.scope`` set to the connection scope (with
``user``, ``session``, ``request`` and ``event_type``). Use it, for example, in
``save()``:

.. code-block:: python

   def save(self, *args, **kwargs):
       if self.user_id is None:
           self.user = self.scope["user"]
       super().save(*args, **kwargs)

Instances of list and named views have no scope; outside the consumer it is
``None``.

Success messages
~~~~~~~~~~~~~~~~

After a successful save or create the response carries a ``header`` and
``msg`` that the client shows through ``pushMsg``. The texts come from
``templates/sdc_strings.json`` (keys ``save``, ``create``, ``on_change``,
``delete`` per model, ``{0}`` is replaced with ``str(instance)``). With
``DEBUG`` on, the file is created and missing models are added automatically.

Client-side model architecture
------------------------------

The browser-side model layer is built around:

``SdcModel``
   One client-side model object.

``SdcQuerySet``
   A live collection wrapper used to load, update, create, save, delete, and
   render models. Each queryset has its own WebSocket.

Model classes must be registered on the client. You normally don't write this
yourself: ``python manage.py sdc_make_model_js`` generates one class per SDC
model in ``Assets/src/models/<Model>.js`` plus ``Assets/src/models/src.js``,
which registers all of them. ``index.organizer.js`` imports ``src.js``, and the
gulp build (``yarn build`` / ``yarn develop``) runs ``sdc_make_model_js``
automatically. The generated registration looks like this:

.. code-block:: javascript

   import { registerModel } from "sdc_client";
   import Book from "./Book.js";

   registerModel("Book", Book);

The structure of the generated classes is described in
:ref:`sdc-model-generated-classes`.

Querysets in controllers
------------------------

Controllers usually create querysets through ``this.querySet(...)``:

.. code-block:: javascript

   class CatalogController extends AbstractSDC {
     async onLoad($html) {
       this.books = this.querySet("Book", { available: true });
       await this.books.load();
       return super.onLoad($html);
     }
   }

``this.querySet(modelName, modelQuery = {})``
   Creates a ``new SdcQuerySet(modelName, modelQuery)`` and registers it on the
   controller. Registered querysets are closed when the controller is removed.

``this.newModel(modelName, modelQuery = {})``
   Deprecated alias of ``querySet()``; logs a warning.

``this.noOpenModelRequests()``
   Resolves when all registered querysets have no open requests.

A queryset created with ``new SdcQuerySet(...)`` directly is not registered
and must be closed by you.

``SdcQuerySet`` behavior
------------------------

Querysets behave like array-like collections:

- ``queryset.length``
- ``queryset[0]``
- iteration via ``for ... of``
- ``getIds()``
- ``byId(id)`` — the cached item with that id, or ``null``

Items loaded from the server are kept sorted by id; ``new()`` appends.

Loading and re-synchronizing data
---------------------------------

``load(modelQuery = null)``
   Clears the current queryset cache and fetches matching rows. A given
   ``modelQuery`` replaces the queryset filter.

``update({ modelQuery = null, item = null })``
   Alternative to ``load()`` when an existing queryset should be synchronized
   again. It can refresh the current filter, a supplied filter, or one specific
   item (``{id: item.id}`` is sent for that request). Existing items are updated
   in place, new ones are added; nothing is removed. The argument object is
   required: call ``update({})``, not ``update()``.

Typical usage:

- use ``load()`` for the initial fetch
- use ``update({})`` to re-sync an existing queryset
- use ``update({ item })`` when one known model should be refreshed

``update``, ``delete``, ``listView``, ``detailView`` and ``view`` all take one
options object without a default, so always pass at least ``{}``.

Both resolve with the raw response message, not the queryset. Its
``args.data`` is the array of loaded ``SdcModel`` instances (the same objects
that are now in the queryset); ``args.media_url`` is ``settings.MEDIA_URL``:

.. code-block:: javascript

   const res = await books.load({ author: 1 });
   res.args.data;   // [Book, Book, ...]
   books.length;    // same items

Results and errors
------------------

All request methods return promises that are rejected with an
``SdcModelError`` when the server answers with an error. It extends ``Error``
and has:

``msg``
   Error text (for validation errors an HTML ``<ul>`` of field errors).
``header``
   Short title.
``is_error``
   ``true``.
``html``
   Only for save/create validation errors: the re-rendered form with errors.

Every server response that carries a ``msg`` or ``header`` also triggers the
global event ``pushMsg(header, msg)`` or, for errors, ``pushErrorMsg(header,
msg)``, which the ``sdc-alert-messenger`` controller displays. Successful saves
and creates therefore show a notification without extra code.

Other queryset methods
----------------------

``new(values = {})``
   Creates a new model instance, pre-filled with ``values``, and attaches it to
   the queryset. Nothing is sent to the server.

``get(modelQuery = null, doNotLoad = false)``
   Async. Loads and returns exactly one item; the promise is rejected if the
   result count is not one. On success ``{id}`` is added to the filter. With
   ``doNotLoad = true`` it returns the cached item with the given ``id`` (or a
   new instance) without a server request.

``setFilter(modelQuery)`` / ``addFilter(modelQuery)``
   Replace or merge queryset filters. Both return the queryset. The filter is
   sent with every request and is used by the server for live updates (see
   :ref:`sdc-model-live-updates`).

``setIds(ids)``
   Rebuild the queryset from ids and set the filter to ``{id__in: [...]}``.
   ``ids`` may be a number, an array of numbers or numeric strings, a
   comma-separated string such as ``"1,2"``, ``null``/``""``/``[]`` (empty), an
   ``SdcModel`` or another ``SdcQuerySet``. Cached items with matching ids are
   kept; missing ids become new, unloaded instances that contain only the id.
   Call ``load()`` to fetch their data. Returns the new item list.

   .. note::

      For an ``SdcModel`` or ``SdcQuerySet`` argument the items are copied with
      ``structuredClone``. This throws a ``DataCloneError`` for instances that
      belong to a queryset or have relation fields (they hold a ``WeakRef`` or
      queryset proxies). Pass ids instead.

``save({ pk = null, id = null, formName = "edit_form", data = null } = {})``
   Save existing items. With ``pk`` (or its alias ``id``) only that item is
   saved; without it, every item in the queryset is saved, one request each.
   ``data`` replaces the serialized model values. ``formName`` selects a named
   form of ``SdcMeta``; unknown names fall back to ``edit_form``. ``File``
   values are uploaded first. Resolves to an array of responses; each
   ``res.data.instance`` is an array with the updated ``SdcModel``. Rejects
   with ``SdcModelError`` if ``pk`` is not in the queryset or the form is
   invalid.

``create(data)`` / ``create({ elem, data })``
   Create a new backend item. Pass the field values directly
   (``create({title: "Dune"})``) or an options object with ``elem`` (an existing
   unsaved ``SdcModel``) and/or ``data``. Without ``elem``, a new instance is
   created with ``new(data)``. The request sends ``data``, or
   ``elem.serialize()`` when no data is given. On success ``elem.id`` is set
   and ``res.data.instance`` is the created ``SdcModel`` (a single object, not
   an array).

``delete({ pk = null, id = null, elem = null })``
   Delete an item by id (``pk`` or ``id``) or model object. Throws synchronously
   if none is given. The item is not removed from the local queryset.

Server-rendered views
---------------------

Querysets can render model-backed HTML fragments from the server. All three
methods return a jQuery ``<div class="container-fluid">`` **synchronously**.
The server HTML is appended to it when the response arrives, and the div is
passed through the SDC refresh pipeline so nested controllers and events
continue to work. Insert the div right away:

.. code-block:: javascript

   this.find(".book-list").append(this.books.listView({}));

``listView({ modelQuery = {}, searchValues = {}, cbResolve = null, cbReject = null, templateContext = {} })``
   Renders ``html_list_template``. The request filter is the queryset filter
   merged with ``modelQuery``. ``searchValues`` is sent as
   ``__search_values``; the server removes it from the filter and passes it to
   the template context as ``filter`` (the generated ``render()`` feeds it into
   the search form). ``templateContext`` becomes ``template_context``.

``detailView({ pk, cbResolve = null, cbReject = null, templateContext = {} })``
   Renders ``html_detail_template`` for one instance. The loaded instance is
   added to (or updated in) the queryset.

``view({ viewName = "html_list_template", modelQuery = {}, cbResolve = null, cbReject = null, templateContext = {} })``
   Renders the template named by ``SdcMeta.<viewName>`` with ``instances``.
   ``modelQuery`` is used as is; it is **not** merged with the queryset filter.
   The loaded instances are added to the queryset.

``cbResolve(res)`` is called after the HTML was inserted, ``cbReject(err)`` on
error. There is no returned promise.

.. note::

   The response of ``listView()`` also contains the loaded rows, but the client
   only turns ``load``, ``named_view`` and ``detail_view`` responses into model
   objects. ``listView()`` does not add items to the queryset.

Uploads and connection lifecycle
--------------------------------

If a model contains ``File`` values, the queryset uploads them in chunks of
25000 bytes before the final ``save()`` or ``create()`` request.

Each queryset also manages its own connection state:

``isConnected()``
   Opens the socket if needed and performs the ``connect`` handshake (sending
   the current filter). Every request method calls it, so you rarely need it
   directly. Concurrent callers share one connection attempt. If the server
   refuses the ``connect`` (``is_authorised`` returns ``False``), the promise is
   rejected and the socket is closed without reconnecting.

``close()``
   Closes the socket, disables auto-reconnect and closes the relation
   querysets of all contained items.

``noOpenRequests()``
   Resolves when all outstanding requests are complete.

``onUpdate`` / ``onCreate`` (setter aliases ``on_update`` / ``on_create``)
   React to pushed model events; see :ref:`sdc-model-live-updates`.

If the socket closes unexpectedly, all open requests are rejected with the
``CloseEvent`` and the queryset reopens the socket after one second (unless
``close()`` was called).

.. note::

   The automatic reconnect only reopens the socket; it does not repeat the
   ``connect`` handshake. The queryset stays marked as not connected, so the
   next request calls ``isConnected()``, which opens another socket and
   performs the handshake there. Until then the queryset receives no live
   updates.

``SdcModel`` instances
----------------------

An ``SdcModel`` is one row on the client. Instances are created by querysets
(``load()``, ``new()``, ...) or directly with ``new Book({...})``; an instance
created directly has no queryset, so the methods below that talk to the server
do not work on it.

``id`` / ``pk``
   Primary key; ``pk`` is an alias. ``null`` for unsaved instances.
``querySet``
   Getter for the owning queryset (held as a ``WeakRef``).
``loaded``
   ``true`` if the data came from the server.
``static fields``
   Field schema of the class (see :ref:`sdc-model-generated-classes`).

``save({ formName = "edit_form", data = null } = {})``
   ``querySet.save({pk: this.id, formName, data})``.

``create(data)`` / ``create({ data })``
   ``querySet.create({elem: this, data})``. Without data the instance is
   serialized.

``delete()``
   ``querySet.delete({elem: this})``.

``load()`` / ``update()``
   ``querySet.update({item: this})``: re-fetches this row and updates the
   instance in place.

``close()``
   Closes the **whole** owning queryset.

``detailView({ cbResolve = null, cbReject = null, templateContext = {} })``
   ``querySet.detailView({pk: this.id, ...})``.

``form({ cbResolve = null, cbReject = null } = {})``
   Server-rendered form: the create form if ``id`` is ``null`` or ``-1``,
   otherwise the edit form. See :ref:`sdc-model-forms`.

``namedForm({ formName, cbResolve = null, cbReject = null })``
   Renders the form ``SdcMeta.<formName>`` for an existing instance.

``serialize()``
   Plain object with one entry per field, as sent to the server: to-many
   relations as id arrays, to-one relations as id or ``null``, ``DateField`` as
   ``"YYYY-MM-DD"``, ``DateTimeField`` as ``toISOString()``, other values
   unchanged.

``toJson()``
   Plain object for display or debugging: ``File`` as its name, related models
   as id, querysets as id arrays, other values (including ``Date``) unchanged.

``setValues(data)``
   Assigns all fields from ``data`` (``pk`` is accepted for ``id``). Invalid
   values are ignored silently.

``validate(value, config)``
   Throws an ``Error`` if ``value`` is not valid for the field config
   (required, ``max_length``, type checks). Generated setters call it, so
   ``book.title = 42`` throws ``"Must be a string"``.

``parseValue(value, config)``
   Converts a raw value to the field's JavaScript type; see
   :ref:`sdc-model-field-types`.

.. _sdc-model-forms:

Forms and ``SdcModel`` synchronization
--------------------------------------

The important rule for SDC model forms is:

``SdcModel`` properties and form fields must stay synchronized.

The form is not treated as an independent state store. It is a view of the
model object. This is central to the framework because controller form
submission works on the bound model instance, not on a detached raw payload.

The ``SdcModel`` object therefore remains the source of truth across edit,
create, save and validation error flows, and later refreshes of the same item.

Rendering a form
~~~~~~~~~~~~~~~~

.. code-block:: html

   <form class="book-form"></form>

.. code-block:: javascript

   const book = await this.books.get({ id: 3 });
   this.find(".book-form").append(book.form());

   const draft = this.books.new();
   this.find(".new-book-form").append(draft.form());   // create form

``form()`` and ``namedForm()`` return a ``<div>`` that is filled when the server
responds. Put that div inside a ``<form>`` element: the client attaches the
metadata needed by the controller submit flow to the closest ``<form>``, and
without one nothing is attached:

- classes ``sdc-model-form``, ``sdc-model-create-form`` or
  ``sdc-model-edit-form``, and the model's ``formId``
- ``data("model", modelObj)``
- ``data("model_pk", pk)`` (``-1`` for new instances)
- ``data("form_name", formName)``
- ``sdc_submit="submitModelFormDistributor"`` when absent

The form is also registered on the model object with ``addForm()`` so later
sync operations know which forms belong to it.

Live synchronization
~~~~~~~~~~~~~~~~~~~~

``addForm($form)``
   Registers a jQuery form on the model and listens to ``input`` and ``change``
   events of its ``input``, ``select`` and ``textarea`` elements. When a field
   whose ``name`` is a model field changes, the model's
   ``set<name>(getValueFromField(el))`` method is called. Called automatically
   by ``form()`` and ``namedForm()``; calling it twice for the same form adds
   the listeners twice.

Assigning a model property (``book.title = "Dune"``) writes the value into the
fields with that name in all registered forms. Form edits update the model but
are not written back to other forms, because they call the ``set<name>()``
method rather than the property setter.

Every assignment is validated. An invalid value makes the setter throw; from a
form event the error is thrown inside the event handler and the model keeps the
previous value.

Explicit synchronization
~~~~~~~~~~~~~~~~~~~~~~~~

``syncModelToForm($forms)``
   Writes the model state into the form fields of all given forms whose
   ``model_pk`` equals the model ``id``.

``syncForm($forms)``
   Reads all named form fields back into the model object (through the property
   setters) and returns the values as a plain object, including fields that are
   not model fields. Forms whose ``model_pk`` does not match are skipped; a new
   model (``id`` ``null``) matches ``model_pk`` ``-1``.

``syncFormToModel($forms)``
   Alias of ``syncForm()``.

Both methods only use ``$forms`` if it has the model's ``formId`` class (i.e.
it was rendered by ``form()``/``namedForm()`` for this instance); otherwise they
use all forms rendered for this instance.

.. note::

   Because of the ``model_pk`` check, ``syncModelToForm()`` does nothing for
   create forms of new models (``id`` is ``null``, ``model_pk`` is ``-1``).
   ``syncForm()`` uses the validating setters, so it throws on the first
   invalid value, e.g. an empty required field.

Practical consequences:

- updating the model is reflected in the form
- editing the form updates the ``SdcModel`` object
- hidden fields are converted back to native JavaScript types (``"true"``,
  numbers, ``"None"`` → ``null``, quoted strings)
- checkboxes give booleans
- file inputs are stored as ``File`` objects on the model until upload
- relation fields are converted into related ids or queryset-backed relations

Submitting model forms
~~~~~~~~~~~~~~~~~~~~~~

The form's ``sdc_submit`` handler ``submitModelFormDistributor($form, e)`` on
the controller calls the first of these that exists:

1. ``this._submitModelForm($form, e)``
2. ``this.submitModelForm($form, e)`` — define this to replace the default flow
3. ``this.defaultSubmitModelForm($form, e)``

The default flow prevents the native submit, runs
``model.syncForm($form)``, then calls ``model.save({formName, data})`` for
existing models or ``model.create({data})`` for new ones. On success it clears
the form errors and calls ``submit_model_form_success(res[0])`` on the
controller and on all its child controllers, if defined. On failure it
reconciles the error HTML into the first ``.container-fluid`` element inside the
form and calls ``submit_model_form_error(err)`` (with the ``SdcModelError``) on
the controller and its children.

.. code-block:: javascript

   class BookEditController extends AbstractSDC {
     submit_model_form_success(res) {
       this.find(".status").text("Saved");
     }

     submit_model_form_error(err) {
       console.warn(err.header, err.msg);
     }
   }

.. note::

   ``save()`` resolves with an array of responses, so ``res[0]`` is the
   response. ``create()`` resolves with a single response object, so in the
   create flow ``res[0]`` is ``undefined`` and
   ``submit_model_form_success`` receives ``undefined``.

Validation errors
~~~~~~~~~~~~~~~~~

When the backend returns validation errors, the client reconciles the returned
form HTML back into the page rather than throwing away the whole subtree. This
preserves controller structure while keeping the current ``SdcModel`` instance
active. ``namedForm()`` wraps the form in a ``.container-fluid`` div, so the
error HTML replaces that fragment; for ``form()`` the target is the first
``.container-fluid`` inside the rendered form HTML.

.. _sdc-model-field-types:

Field types and value conversion
--------------------------------

Generated setters call ``validate()`` and then ``parseValue()``, so every
field holds a JavaScript type:

.. list-table::
   :header-rows: 1

   * - Django field
     - Value on the model
   * - ``CharField``, ``EmailField``, ``UUIDField``
     - string (``EmailField`` and ``UUIDField`` are format-checked)
   * - ``TextField``
     - validated as a string, stored unchanged (the conversion switch lists
       ``TeextField``)
   * - ``IntegerField``, ``AutoField``, ``BigIntegerField``
     - ``parseInt(value, 10)``
   * - ``FloatField``, ``DecimalField``
     - ``parseFloat(value)`` (Django sends decimals as strings)
   * - ``BooleanField``
     - boolean; the value must already be a boolean
   * - ``DateField``, ``DateTimeField``
     - ``Date`` or ``null`` (see below)
   * - ``URLField``
     - ``URL`` object
   * - ``JSONField``
     - object; a string would be parsed, but ``validate()`` rejects strings
       first, so assign objects
   * - ``FileField``
     - ``FileLoaded`` for stored files, ``File`` for new uploads, ``null``
   * - relations
     - see :ref:`sdc-model-generated-classes`; string values are
       ``JSON.parse``\ d (``"5"``, ``"[1,2]"``)
   * - other types (e.g. ``BigAutoField``)
     - unchanged, not validated

Dates (0.159.0)
~~~~~~~~~~~~~~~

Since 0.159.0 ``DateField`` and ``DateTimeField`` values are ``Date`` objects
(previously numeric timestamps):

- Reading: values are converted with ``toDate()``. Empty or invalid values
  become ``null``. A date-only string ``"YYYY-MM-DD"`` is read as local
  midnight, not UTC, so the day does not shift west of UTC. Other strings and
  numbers go through ``new Date(value)``.
- Serializing: ``serialize()`` sends a ``DateField`` as ``"YYYY-MM-DD"`` (local
  date) and a ``DateTimeField`` as ``toISOString()`` (UTC).
- Forms: ``<input type="date">`` is filled with ``formatDate()``
  (``YYYY-MM-DD``) and ``<input type="datetime-local">`` with
  ``formatDateTimeLocal()`` (``YYYY-MM-DDTHH:MM``), both in local time; seconds
  are dropped. Values read back from these inputs are parsed with
  ``toDate()`` again.

``toDate``, ``formatDate`` and ``formatDateTimeLocal`` are in
``sdc_utils.js``; the format functions return ``""`` for invalid values.

Files
~~~~~

A stored file arrives as ``{name, url}`` and becomes a ``FileLoaded``:

``name``, ``url``
   From the server.
``load(force = false)``
   Fetches the file content with ``$.get(url)`` once and caches it in
   ``content``; resolves ``""`` on error.
``text()``
   Same as ``load()``.

Selecting a file in a file input sets a ``File`` on the model, which is
uploaded on the next save or create. A string value (e.g. from a hidden input)
becomes ``null``.

.. note::

   The generated schema has ``max_size`` (``5 * 1024 * 1024 * 1024`` bytes,
   i.e. 5 GiB, although the generator comment says 5 MB) and
   ``allowed_types = null``. If a ``File`` violates them, ``parseValue()``
   returns an error message string, which is then stored as the field value
   instead of throwing.

.. _sdc-model-generated-classes:

Generated JavaScript model classes
----------------------------------

``sdc_make_model_js`` deletes and rewrites ``Assets/src/models/`` on every run:
one ``<Model>.js`` per SDC model and ``src.js`` with the ``registerModel()``
calls. Do not edit these files. Each class looks like this (shortened):

.. code-block:: javascript

   import {SdcModel, SdcQuerySet} from 'sdc_client';

   export default class Book extends SdcModel {
     static fields = {
       "title": {"type": "CharField", "required": true, "max_length": 255, ...},
       "author": {"type": "ForeignKey", "is_relation": true, "many_to_one": true,
                  "related_model": "Author", "remote_field": "book", ...},
       ...
     }

     constructor(data = {}) {
       super("Book");
       this._toManyFields = [];
       this._author = new SdcQuerySet('Author');
       this._title = null;
       this.setValues(data || {});
     }

     set title(value) { this.settitle(value); this._updateForm('title'); }
     settitle(value) {
       this.validate(value, Book.fields.title);
       this._title = this.parseValue(value, Book.fields.title);
     }
     get title() { return this._title; }
     ...
   }

``static fields`` has one entry per field (reverse relations use their accessor
name, e.g. ``book_set``), restricted by ``SdcMeta.fields``/``exclude``. Keys:
``type`` (Django internal type), ``required`` (``not null and not blank``),
``max_length``, ``is_relation``, ``many_to_many``, ``one_to_many``,
``many_to_one``, ``one_to_one``, ``related_model`` (class name),
``remote_field``, ``reverse_relation``; ``FileField`` also has ``max_size`` and
``allowed_types``.

For each field there is a property setter, a validating ``set<name>(value)``
method (field name as is, e.g. ``settitle``) and a getter. ``setValues()`` wraps
each assignment in ``try {} catch {}``, so invalid server or constructor values
are dropped silently while direct assignments throw.

Relationships
~~~~~~~~~~~~~

Every relation field is backed by its own ``SdcQuerySet`` of the related model:

To-one (``ForeignKey``, ``OneToOneField``)
   The getter returns the first model of that queryset, or ``new()`` on it (an
   empty model) if it is empty. Assigning an id calls ``setIds(id)``, which
   creates an unloaded stub with only the id; call ``load()`` on it to fetch the
   related row:

   .. code-block:: javascript

      const author = book.author;   // Author stub with id
      await author.load();
      author.name;

To-many (``ManyToManyField``, reverse relations)
   The getter returns the ``SdcQuerySet`` itself. Assigning ids calls
   ``setIds()``. For reverse relations the queryset filter is
   ``{<remote_field>: this.id}``; setting ``id`` on the model resets the filter
   of every to-many queryset to ``{<remote_field>: id}``.

Serialization follows two rules:

- many-to-one and one-to-one relations serialize as one related primary key
- one-to-many and many-to-many relations serialize as a list of related primary
  keys

The relation querysets are not registered on a controller; they are closed when
the owning queryset is closed.

.. note::

   Assign ids to relation fields. Assigning an ``SdcModel`` or ``SdcQuerySet``
   goes through ``setIds()`` and hits the ``structuredClone`` limitation
   described there.

.. note::

   ``SdcModel.querySet(modelQuery, parent)`` (static) reads ``this.modeName``,
   which is not defined, so it creates a queryset without a model name. Use
   ``new SdcQuerySet("Book", ...)`` or ``this.querySet("Book", ...)`` in a
   controller.

.. _sdc-model-live-updates:

Live updates
------------

Every queryset joins a channel group named after its model during the
``connect`` handshake. A Django ``post_save`` or ``post_delete`` signal of any
SDC model serializes the instance and broadcasts it to that group:

- ``post_save`` with ``created=True`` → ``on_create``
- every other ``post_save`` → ``on_update``
- ``post_delete`` → ``on_update`` (there is no delete event)

Each connection then decides whether to forward the event:

``on_update``
   Sent only if the pk is among the ids the connection loaded last (the result
   of the most recent server-side load for that socket).

``on_create``
   Sent only if the new row is found by
   ``get_queryset(user, <last action>, <last filter>)`` plus the sanitised
   filter, i.e. it is visible to that user and matches that connection's
   filter. This check also refreshes the connection's list of loaded ids.

"Last" means the ``model_query`` and action of the most recent message on that
socket. ``update({item})`` and ``detailView()`` send a narrower filter, and
form requests send none (``{}``), which changes what is forwarded afterwards.

On the client the pushed rows are merged into the queryset (existing items are
updated, new ones are added) and the handler is called with the array of
affected models:

.. code-block:: javascript

   this.books = this.querySet("Book", { author: 1 });
   await this.books.load();

   this.books.onUpdate = (books) => this.refreshList(books);
   this.books.on_create = (books) => books.forEach((b) => trigger("pushMsg", "New", b.title));

.. note::

   Deleting a row sends an ``on_update`` with its last data, so a deleted row
   stays in client querysets. ``QuerySet.update()``, ``bulk_create()`` and raw
   SQL do not send signals and therefore produce no live events.

WebSocket protocol
------------------

Routes (``SdcTest/routing.py``):

- ``ws(s)://<host>/sdc_ws/model/<ModelName>`` — the model consumer; the model
  name may also be given in lowercase
- ``ws(s)://<host>/sdc_ws/model/<ModelName>/<id>`` — same consumer; the id is
  ignored by the server and the client never uses it
- ``ws(s)://<host>/sdc_ws/ws/`` — the ``sdc_call`` consumer for server calls,
  not model related

Request (client → server):

.. code-block:: json

   {
     "event": "model",
     "event_type": "save",
     "event_id": "<uuid>",
     "args": {
       "model_name": "Book",
       "model_query": {"author": 1},
       "pk": 3, "id": 3,
       "form_name": "edit_form",
       "data": {"title": "Dune", "author": 1},
       "files": {"cover": {"id": "<upload event_id>", "file_name": "a.png",
                           "field_name": "cover", "content_length": 1234}}
     }
   }

Only the ``args`` needed by the ``event_type`` are sent. ``event_type`` is one
of:

``connect``
   Handshake; loads with the filter and joins the model group.
``load``
   Response ``args: {data, media_url}``; ``data`` is the serializer JSON
   string.
``list_view`` / ``named_view`` / ``detail_view``
   Response ``html`` and ``args: {data, media_url}``. Extra args
   ``view_name`` (named view), ``pk`` (detail view), ``template_context``.
``edit_form`` / ``create_form`` / ``named_form``
   Response ``html``. Args ``pk``, ``form_name``.
``save`` / ``create``
   Args ``data``, ``files``, ``pk`` and ``form_name`` (save). Response
   ``html``, ``data: {instance}`` (serializer JSON string, ``null`` if
   invalid), ``header``/``msg``, and ``is_error: true`` if the form is invalid.
``upload``
   One message per chunk, all with the same ``event_id``: ``chunk`` (array of
   byte values, max. 25000 bytes), ``idx``, ``number_of_chunks``,
   ``file_name``, ``field_name``, ``content_length``, ``content_type``. The
   server answers once, after the last chunk. The ``event_id`` is then passed
   as ``files[field].id`` in ``save``/``create``.
``delete``
   Arg ``pk``. Response without payload.

Response (server → client):

.. code-block:: javascript

   {"type": "<event_type>", "event_id": "<uuid>", "is_error": false, /* event specific keys */}

Error response:

.. code-block:: json

   {"type": "<event_type>", "event_id": "<uuid>", "is_error": true,
    "header": "Upps!!", "msg": "403 Not allowed!"}

Pushed events have ``"type": "on_create"`` or ``"on_update"``,
``"event_id": "none"``, ``pk`` and ``args: {data}``.
