.. _getting-started-label:

Getting Started
===============

This guide shows the standard way to start a new Django project with SDC.

Quick setup
-----------

From a development directory:

.. code-block:: sh

   PROJECT_NAME=mysite
   django-admin startproject $PROJECT_NAME
   cd ./$PROJECT_NAME
   python -m venv venv
   source venv/bin/activate
   pip install simpledomcontrol
   python manage.py sdc_init
   npm install

That gives you:

- a Django project extended with SDC settings
- routing and websocket support files
- base templates
- an ``Assets`` directory for client code
- a ready-to-install JavaScript toolchain and runtime package

Manual setup flow
-----------------

1. Create a Django project.

.. code-block:: sh

   django-admin startproject mysite
   cd mysite

2. Create and activate a virtual environment.

.. code-block:: sh

   python -m venv venv
   source venv/bin/activate

3. Install SDC.

.. code-block:: sh

   pip install simpledomcontrol

4. Initialize the project.

.. code-block:: sh

   python manage.py sdc_init

5. Install client dependencies.

.. code-block:: sh

   npm install

What ``sdc_init`` changes
-------------------------

The initialization command prepares both the Django and client sides of the
project.

Typical server-side changes:

- adds the required SDC Django apps
- prepares template settings
- configures static file handling
- adds routing-related files
- installs base templates such as ``base.html`` and reusable form templates

Typical client-side changes:

- creates the top-level ``Assets`` directory
- prepares the client source structure
- adds webpack/gulp-based build files in existing SDC projects
- installs the JavaScript runtime dependency that powers SDC controllers

Project layout after initialization
-----------------------------------

::

    mysite/
    ├─ Assets/
    │  ├─ src/
    │  ├─ webpack.config/
    │  ├─ gulpfile.js
    │  └─ package.json
    ├─ templates/
    │  ├─ base.html
    │  ├─ index.html
    │  └─ elements/
    ├─ manage.py
    └─ mysite/
       ├─ settings.py
       ├─ routing.py
       └─ ...

Create your first app
---------------------

Create a normal Django app and add it to ``INSTALLED_APPS``:

.. code-block:: sh

   python manage.py startapp main_app

Then add it to the Django settings.

Your first controller
---------------------

Generate a controller:

.. code-block:: sh

   python manage.py sdc_cc -a main_app -c dashboard

This creates the linked controller files in the app-specific asset directory and
the Django template/view wiring for the controller.

Your first model
----------------

Generate a model scaffold:

.. code-block:: sh

   python manage.py sdc_new_model -a main_app -m Book

This creates:

- the Django model class
- its form class
- default list/detail templates
- the hooks required for the SDC client model transport

Where the client docs fit in
----------------------------

Once the project is initialized, the JavaScript runtime documented in
:doc:`client`, :doc:`sdc_controller`, and :doc:`sdc_model` becomes the browser
side of your application.

Those sections explain:

- how controller tags are bootstrapped
- how the lifecycle works
- how DOM events are delegated
- how models and forms stay synchronized in the client
