.. _sdc-model-label:

SDC Models
==========

SDC extends Django models so they can also be used from the browser through the
client runtime. The server remains authoritative, but the client gets typed
model objects, queryset-style access, server-rendered forms and views, and live
updates over WebSockets.

Creating a model
----------------

Generate a model scaffold with:

.. code-block:: sh

   python manage.py sdc_new_model -a <django_app_name> -m <ModelName>

Use CamelCase for the model name.

The command generates:

- a Django model class
- a form class
- default list/detail templates
- the metadata and runtime hooks required by SDC

Server model metadata
---------------------

Generated models use SDC metadata to define the forms and templates used by the
runtime.

Typical fields on ``SdcMeta``:

``edit_form``
   Python import path to the form used for save/update operations.

``create_form``
   Python import path to the form used for create operations.

``html_list_template``
   Template used for server-rendered list views.

``html_detail_template``
   Template used for server-rendered detail views.

These templates are not only presentation helpers. They are part of the model
workflow used by the client for list rendering, detail rendering, and form
submission.

Authorization
-------------


Models are responsible for authorizing their own SDC actions. Two classmethods
work together:

``is_authorised(cls, user, action, obj)``
   Returns whether ``user`` may perform ``action``. ``action`` is one of:
   ``connect``, ``load``, ``list_view``, ``detail_view``, ``edit_form``,
   ``named_form``, ``create_form``, ``save``, ``create``, ``upload``, ``delete``.

``get_queryset(cls, user, action, obj)``
   Returns the rows this user may see or operate on for the given action.

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

Client-side model architecture
------------------------------

The browser-side model layer is built around:

``SdcModel``
   One client-side model object.

``SdcQuerySet``
   A live collection wrapper used to load, update, create, save, delete, and
   render models.

Model classes must be registered on the client:

.. code-block:: javascript

   import { registerModel } from "sdc_client";
   import Book from "./models/Book.js";

   registerModel("Book", Book);

Querysets in controllers
------------------------

Controllers usually create querysets through ``this.querySet(...)``:

.. code-block:: javascript

   class CatalogController extends AbstractSDC {
     onInit() {
       this.books = this.querySet("Book", { available: true });
     }

     async onLoad(html) {
       await this.books.load();
       return super.onLoad(html);
     }
   }

``SdcQuerySet`` behavior
------------------------

Querysets behave like array-like collections:

- ``queryset.length``
- ``queryset[0]``
- iteration via ``for ... of``
- ``getIds()``
- ``byId(id)``

Loading and re-synchronizing data
---------------------------------

``load(modelQuery = null)``
   Clears the current queryset cache and fetches matching rows.

``update({ modelQuery = null, item = null })``
   Alternative to ``load()`` when an existing queryset should be synchronized
   again. It can refresh the current filter, a supplied filter, or one specific
   item.

Typical usage:

- use ``load()`` for the initial fetch
- use ``update()`` to re-sync an existing queryset
- use ``update({ item })`` when one known model should be refreshed

Other queryset methods
----------------------

``new()``
   Creates a new empty model instance and attaches it to the queryset.

``get(modelQuery = null)``
   Loads and returns exactly one item. Raises if the result count is not one.

``setFilter(modelQuery)`` / ``addFilter(modelQuery)``
   Replace or merge queryset filters.

``setIds(ids)``
   Rebuild the queryset from ids, another queryset, or an existing model.

``save({ pk = null, formName = "edit_form", data = null })``
   Save one or more existing items.

``create({ elem, data = null })``
   Create a new backend item.

``delete({ pk = null, elem = null })``
   Delete an item by id or model object.

Server-rendered views
---------------------

Querysets can render model-backed HTML fragments from the server:

- ``listView(...)``
- ``detailView(...)``
- ``view(...)``

The returned container is passed through the SDC refresh pipeline so nested
controllers and events continue to work.

Forms and ``SdcModel`` synchronization
--------------------------------------

The important rule for SDC model forms is:

``SdcModel`` properties and form fields must stay synchronized.

The form is not treated as an independent state store. It is a view of the
model object.

The synchronization happens in both directions:

``syncModelToForm($form)``
   Writes the model state into the form fields.

``syncForm($form)``
   Reads the form fields back into the model object and returns the submission
   data.

This is central to the framework because controller form submission works on the
bound model instance, not on a detached raw payload.

Practical consequences:

- updating the model should be reflected in the form
- editing the form should update the ``SdcModel`` object
- hidden fields are converted back to native JavaScript types
- file inputs are stored as ``File`` objects on the model until upload
- relation fields are converted into related ids or queryset-backed relations

The ``SdcModel`` object therefore remains the source of truth across:

- edit flows
- create flows
- save flows
- validation error flows
- later refreshes of the same item

How rendered forms are attached
-------------------------------

When the client requests a create or edit form, it attaches the metadata needed
by the controller submit flow:

- ``data("model", modelObj)``
- ``data("model_pk", pk)``
- ``data("form_name", formName)``
- ``sdc_submit="submitModelFormDistributor"`` when absent

The form is also registered on the model object so later sync operations know
which forms belong to it.

Validation errors
-----------------

When the backend returns validation errors, the client reconciles the returned
form HTML back into the page rather than throwing away the whole subtree. This
preserves controller structure while keeping the current ``SdcModel`` instance
active.

Relationships
-------------

Client-side model tests show two main serialization rules:

- many-to-one relations serialize as one related primary key
- one-to-many relations serialize as a list of related primary keys

This allows richer client-side relation handling while keeping backend payloads
simple.

Uploads and connection lifecycle
--------------------------------

If a model contains ``File`` values, the queryset uploads them in chunks before
the final ``save()`` or ``create()`` request.

Each queryset also manages its own connection state:

- ``isConnected()`` ensures the WebSocket handshake is complete
- ``close()`` closes the queryset connection
- ``noOpenRequests()`` resolves when all outstanding requests are complete
- ``onUpdate`` and ``onCreate`` can react to pushed model events
