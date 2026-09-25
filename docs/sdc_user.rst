.. _sdc-user-label:

User management (sdc_user)
==========================

``sdc_user`` is the user app shipped with SDC. ``sdc_init`` adds it to
``INSTALLED_APPS`` and wires its views under ``sdc_view/sdc_user/``. It
provides:

- ``SdcUser``, a custom user model that is also an SDC model
- ready-made controllers for login, logout, registration, password reset and
  e-mail confirmation
- e-mails for e-mail confirmation and password reset
- settings to control who may read and change user data

The SdcUser model
-----------------

``SdcUser`` extends Django's ``AbstractUser`` and ``SdcModel``, so it has all
fields of Django's default user (``username``, ``email``, ``first_name``,
``last_name``, ``password``, ``is_staff``, ``is_superuser``, ``groups``, …) and
can be used with querysets on the client and with the :ref:`sdc-rest-api-label`.
It adds one field:

``email_confirmed``
   ``BooleanField``, default ``False``. Set to ``True`` when the user opens the
   link of the confirmation e-mail. It is **not** checked at login.

Its ``SdcMeta``:

``edit_form``
   ``sdc_user.forms.SdcUserChangeForm`` — ``username``, ``first_name``,
   ``last_name``, ``email`` and a read-only ``password`` field (see
   `ReadOnlyPassword widget`_).

``create_form``
   ``sdc_user.forms.SdcUserCreationForm`` — ``username``, ``first_name``,
   ``last_name``, ``email``, ``password1`` and ``password2``. The password is
   checked with Django's password validators and stored hashed.

``password_form``
   ``sdc_user.forms.SdcUserPassword`` — ``password_old``, ``password1`` and
   ``password2``. Used as a named form to change the password.

``html_list_template`` / ``html_detail_template``
   ``sdc_user/models/SdcUser/SdcUser_list.html`` and
   ``sdc_user/models/SdcUser/SdcUser_details.html``.

``fields`` / ``exclude``
   Taken from ``SDC_USER_FIELDS`` and ``SDC_USER_FIELDS_EXCLUDE``.

The model also has a ``SearchForm`` (search in ``username``, ``first_name``,
``last_name``, ``email``) used by the list view.

Whenever an ``SdcUser`` is saved with an e-mail address that differs from the
one the Python instance had when it was created or loaded, a confirmation
e-mail is sent (see `E-mails`_). This includes new users registered through a
form. Users created with ``SdcUser.objects.create_user(..., email=...)`` get no
e-mail, because the address is already set when the instance is created.

.. note::

   The remembered address is not updated after ``save()``. Saving the same
   Python instance again sends another confirmation e-mail.

``AUTH_USER_MODEL``
-------------------

``sdc_init`` writes

.. code-block:: python

   AUTH_USER_MODEL = "sdc_user.SdcUser"

*./root_dir/<project>/settings.py*

so ``SdcUser`` replaces Django's ``auth.User``. Django only supports this
setting when it is set before the first ``migrate``. For a new project, run
``sdc_init`` first and ``migrate`` afterwards. Refer to the user model with
``django.contrib.auth.get_user_model()`` or ``settings.AUTH_USER_MODEL``, not
with ``django.contrib.auth.models.User``.

Migrating an existing project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If your database has already been migrated with ``auth.User``, convert it with:

.. code-block:: sh

   python manage.py sdc_db_tools --update_to_sdc_user
   python manage.py sdc_db_tools --update_to_sdc_user -p ./backup/before_sdc_user

Run it in the directory of *manage.py*. The command:

1. Writes a temporary settings module *temp_setting.py* next to your settings
   that imports them and deletes ``AUTH_USER_MODEL``, so the old ``auth.User``
   is active.
2. With these settings, runs ``migrate`` and then
   ``sdc_db_tools -b`` to back up the data of all models as JSON files (one
   file ``<app>__<Model>.json`` per model) into the backup directory
   (``-p``/``--path``, default ``./backup/<timestamp>``). The directory must be
   empty or not exist. The temporary settings file is removed afterwards.
3. If a user backup (*auth__User.json*) exists, rewrites its entries to
   ``sdc_user.sdcuser``, **drops all tables** of the database, runs
   ``makemigrations`` and ``migrate`` with the new user model, and restores
   the backup. Primary keys are kept, so foreign keys to users stay valid.

.. warning::

   The command drops all tables. Make your own database backup first, and keep
   the JSON backup directory until you have checked the result. If a step
   fails, the error is printed and the command stops; the backup can be
   restored with ``python manage.py sdc_db_tools -r -p <backup directory>``.
   If there are no users, only the backup is written and the database is not
   changed.

Controllers
-----------

The controllers are registered by ``sdc_user.organizer.js``, which ``sdc_init``
links into your assets. Their server views are in *sdc_user/sdc_views.py*. Use
them as tags or navigate to them with navigation links (see
:ref:`sdc-how-to-nav`):

.. code-block:: html

   <a class="navigation-links" href="/sdc-login">Login</a>
   <a class="navigation-links" href="/register?model=SdcUser&next=..">Register</a>
   <a class="navigation-links" href="/*/sdc-password-forgotten">Password forgotten</a>
   <sdc-logout></sdc-logout>

``sdc-login`` — ``<sdc-login></sdc-login>``
   Login form (Django's ``AuthenticationForm``) with links to
   *Password forgotten* (``/*/sdc-password-forgotten``) and *Register*. The form
   is posted with the ``sdc-auto-submit`` mixin. On success the user is logged
   in with a Django session and the server answers with a redirect to ``next``;
   the controller then loads that URL with ``location.assign()``, i.e. the whole
   page reloads. ``next`` is the ``next`` parameter of the login page, or
   ``LOGIN_SUCCESS`` if it is missing. Errors are shown as an error message.
   ``contentReload`` is set, so the form is fetched fresh every time.

``sdc-logout`` — ``<sdc-logout></sdc-logout>``
   A *Logout* button. Posting it logs the user out and redirects to
   ``/~<LOGIN_CONTROLLER>``. The controller then reconnects the WebSocket
   (``socketReconnect()``) and triggers the ``logout`` event.

``register`` — ``<register></register>``
   Registration form. The controller uses the ``sdc-model-form`` mixin with the
   model ``SdcUser``: without ``pk`` it shows ``SdcUserCreationForm`` and
   creates a new user over the WebSocket; with ``pk`` it shows the edit form.
   It accepts the parameters of ``sdc-model-form`` (``next``, ``pk``,
   ``form_header``, …). Link: ``/register?model=SdcUser&next=..``.

``sdc-password-forgotten`` — ``<sdc-password-forgotten></sdc-password-forgotten>``
   Asks for a user name or e-mail address. The *Send E-mail* button calls the
   server method ``send_email``, which looks the user up by
   ``USERNAME_FIELD`` or ``email`` and sends the password reset e-mail. If no
   user or more than one user matches, it answers ``User not found``.

``sdc-reset-password`` — ``<sdc-reset-password></sdc-reset-password>``
   Target of the reset e-mail. Parameter ``token``. Shows a form with the new
   password twice (Django password validators, minimum 8 characters) and the
   token as hidden field. On submit the token is checked (signature, type
   ``reset``, expiry, single use) and the new password is set. An expired
   token triggers a new e-mail.

``sdc-confirm-email`` — ``<sdc-confirm-email data-token="..."></sdc-confirm-email>``
   Target of the confirmation e-mail. Parameter ``token`` (part of the content
   URL ``sdc_confirm_email/<token>``). A valid token sets ``email_confirmed`` to
   ``True`` and shows *E-Mail successfully confirmed*; otherwise an error
   message is shown. An expired token triggers a new e-mail.

``sdc-change-password`` — ``<sdc-change-password></sdc-change-password>``
   Lets the logged-in user change their password: renders ``sdc-model-form``
   with the ``password_form`` (current password, new password, confirmation)
   of their own ``SdcUser``. Requires login; anonymous users are sent to the
   login controller. Link to it with ``href="/sdc-change-password"``.

``sdc-user`` — global controller
   Registered with ``app.registerGlobal``, so one instance is created at start-up
   without a tag in your page. It asks the server (server call
   ``get_user_id``) for the id of the logged-in user, loads that ``SdcUser``
   through a queryset and stores it in ``this.user``. Other controllers can get
   it with the ``getUser`` event:

   .. code-block:: javascript

      import {trigger} from 'sdc_client';

      const [user] = await trigger('getUser');

   ``user`` is ``null`` for anonymous users and until the queryset has been
   loaded.

``sdc-user-nav-btn`` — ``<sdc-user-nav-btn></sdc-user-nav-btn>``
   Navigation-bar block. For a logged-in user it shows an *Edit <username>*
   link (``/sdc-model-form?model=SdcUser&pk=<pk>``) and ``<sdc-logout>``; for
   anonymous users *Login* (``/<LOGIN_CONTROLLER>``) and *Register*. It reloads
   itself on the ``login`` and ``logout`` events.

.. note::

   The ``send_email`` and ``get_user_id`` server methods use the Django request
   (``request.scheme``, ``request.get_host()``, ``request.user``). They work with
   the default HTTP transport of server calls, but not with
   ``SERVER_CALL_VIA_WEB_SOCKET = True``, where the first argument is the
   consumer instead of a request.

Login flow settings and events
------------------------------

``sdc_init`` writes:

.. code-block:: python

   LOGIN_CONTROLLER = 'sdc-login'
   LOGIN_SUCCESS = '/'

*./root_dir/<project>/settings.py*

``LOGIN_CONTROLLER``
   Controller tag of the login page. ``SdcLoginRequiredMixin`` and
   ``SdcGroupRequiredMixin`` redirect unauthenticated users there (with
   ``next=..``), ``sdc-logout`` redirects there after logout, and
   ``sdc-user-nav-btn`` links to it.

``LOGIN_SUCCESS``
   Default redirect target after login if the login page has no ``next``
   parameter.

Client events:

``login``
   Triggered by ``sdc-login`` only if the login response is not a redirect.
   The built-in view always redirects on success, so after a normal login the
   page reloads and controllers start again instead.

``logout``
   Triggered by ``sdc-logout`` after a logout. ``sdc-user-nav-btn`` and
   ``sdc-navigator`` listen to it.

To react in your own controller, register a handler with ``on``:

.. code-block:: javascript

   import {AbstractSDC, app, on} from 'sdc_client';

   class MenuController extends AbstractSDC {
     onLoad($html) {
       on('logout', this);
       return super.onLoad($html);
     }

     logout() {
       this.reload();
     }
   }

.. note::

   Changing the password with ``password_form`` or ``sdc-reset-password`` calls
   ``set_password()`` without ``update_session_auth_hash()``. Django therefore
   ends the existing sessions of that user and they have to log in again.

E-mails
-------

``sdc_user`` sends two HTML e-mails (templates *email/confirm.html* and
*email/reset_password.html*):

Confirmation
   Sent when a user is saved with a new e-mail address. Subject
   *Confirmation*. The link opens ``sdc-confirm-email``:
   ``<home>/~sdc-confirm-email~&1.token=<token>``.

Password reset
   Sent by ``sdc-password-forgotten``. Subject *Reset Password*. The link opens
   ``sdc-reset-password``: ``<home>/~sdc-reset-password~&1.token=<token>``.

Both tokens are JWTs signed with ``JWT['secret']`` and ``JWT['algorithm']``,
valid for three days and single use: the confirmation token is bound to the
user's e-mail address and ``email_confirmed``, the reset token to the current
password hash. When an expired link is opened, a fresh e-mail is sent.

``<home>`` is determined in this order:

1. the origin of the current request (password forgotten, expired links)
2. the ``Origin`` header of the WebSocket connection, if the user was saved
   through an SDC queryset
3. ``settings.HOME_URL``

Required settings:

``HOME_URL``
   Base URL of your site, e.g. ``"https://example.com"``. It is used when the
   URL cannot be taken from the request, e.g. when a user's e-mail changes in
   the Django admin, the shell or the REST API. ``sdc_init`` defines it (from the
   ``HOME_URL`` environment variable, else the first ``ALLOWED_HOST`` URL, else
   ``http://127.0.0.1:8000`` in ``DEBUG``). If no URL is available at all, the
   e-mail is not sent and an error is logged; the user is still saved.

``DEFAULT_FROM_EMAIL`` and ``EMAIL_*``
   Sender address and SMTP connection. ``sdc_init`` writes these only as
   comments:

   .. code-block:: python

      # EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'
      # EMAIL_HOST =''
      # EMAIL_PORT = 587
      # EMAIL_HOST_USER = ''
      # DEFAULT_FROM_EMAIL = ''
      # EMAIL_HOST_PASSWORD = ''
      # EMAIL_USE_TLS = True

   Uncomment and fill them in. Otherwise Django's defaults apply
   (``webmaster@localhost``, SMTP on ``localhost:25``). During development
   ``EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'`` prints
   the e-mails to the console.

.. note::

   E-mails are sent with ``fail_silently=True``. SMTP errors are not reported;
   the user simply receives no e-mail.

Access settings
---------------

``sdc_init`` writes:

.. code-block:: python

   SDC_USER_GET_QUERYSET = "sdc_user.models.sdc_user_get_queryset"
   SDC_USER_IS_AUTHORISED = "sdc_user.models.sdc_user_is_authorised"
   SDC_USER_FIELDS = "__all__"
   SDC_USER_FIELDS_EXCLUDE = None

*./root_dir/<project>/settings.py*

All four settings are required; they are read when *sdc_user/models.py* is
imported.

``SDC_USER_IS_AUTHORISED``
   Import path of a function ``(user, action, obj)`` used as
   ``SdcUser.is_authorised()``. The actions are the same as for every SDC
   model (``connect``, ``load``, ``create``, ``save``, ``delete``, …, see
   :ref:`sdc-model-label`).

   Default: ``sdc_user.models.sdc_user_is_authorised``:

   - superusers may do everything;
   - anyone, including anonymous users, may use ``connect``, ``create_form``
     and ``create`` (this is what makes ``register`` work);
   - logged-in users may use ``load``, ``list_view``, ``detail_view``,
     ``named_view``, ``edit_form``, ``named_form`` and ``save``, on the rows
     returned by ``SDC_USER_GET_QUERYSET`` (by default only their own user);
   - ``delete`` and ``upload`` are for superusers only.

``SDC_USER_GET_QUERYSET``
   Import path of a function ``(sdc_user_cls, user, action, obj)`` used as
   ``SdcUser.get_queryset()``. Note the extra first argument, the model class.

   Default: ``sdc_user.models.sdc_user_get_queryset`` — superusers get all
   users, everybody else only their own user (anonymous users none).

``SDC_USER_FIELDS``
   ``SdcMeta.fields`` of ``SdcUser``. Default ``"__all__"``.

``SDC_USER_FIELDS_EXCLUDE``
   ``SdcMeta.exclude`` of ``SdcUser``. Default ``None``. Only one of
   ``SDC_USER_FIELDS`` and ``SDC_USER_FIELDS_EXCLUDE`` may be set to a list.

The ``password`` field (the password hash) is never sent to clients and cannot
be used in filters, whatever these two settings say.

.. note::

   The default lets every user read and edit their own ``username``,
   ``first_name``, ``last_name`` and ``email``, and still exposes fields such as
   ``is_staff`` and ``last_login`` of rows a user may load. To change this, set
   ``SDC_USER_IS_AUTHORISED`` to your own function and list the fields to hide
   in ``SDC_USER_FIELDS_EXCLUDE``, for example:

   .. code-block:: python

      SDC_USER_IS_AUTHORISED = "main_app.user_access.sdc_user_is_authorised"
      SDC_USER_FIELDS_EXCLUDE = ["is_superuser", "is_staff", "groups",
                                 "user_permissions", "last_login"]

ReadOnlyPassword widget
-----------------------

``sdc_user.widgets.ReadOnlyPassword`` is the widget of the ``password`` field in
``SdcUserChangeForm``. It does not show the password or its hash, only a
*Reset Password* link that opens ``sdc-model-form`` with the user's
``password_form`` (``form_name=password_form&auto_save=false``). The form's
``clean_password()`` always returns the initial value, so the edit form never
changes the password. The widget renders
*widgets/read_only_password_hash.html* and gets the edited user through its
``user`` attribute, which ``SdcUserChangeForm`` sets.
