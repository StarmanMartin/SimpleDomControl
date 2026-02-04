.. _getting-started-label:

Version 0.57.21
================


Getting Started
===============

In the following steps, we provide a brief introduction on how to initiate a new project. Throughout this introduction, we will refer to the project as *'mysite'*.


To start a new SDC project, open your command line and cd to the directory
where you want to start your code. Then, execute the following commands:

.. code-block:: sh

    $ pip install simpledomcontrol
    $ sdc new



Quick and dirty
***************

Navigate to your project container directory and run the following cli commands:

.. code-block:: sh

    PROJECT_NAME=<ADD_PROJECT_NAME>
    pip install django
    django-admin startproject $PROJECT_NAME
    cd ./$PROJECT_NAME
    virtualenv venv
    source venv/bin/activate
    pip install simpledomcontrol
    sed -i "s/INSTALLED_APPS = \[/INSTALLED_APPS = ['sdc_core',/g" ./$PROJECT_NAME/settings.py
    python manage.py sdc_init
    npm install


Start new Django project
************************

Before you begin, you'll need to create a new Django project.
If you're new to Django, there are some initial setup steps to follow.
Specifically, you'll need to auto-generate some code that establishes
a Django project – a set of configurations for a Django instance,
including database settings, Django-specific options,
and application-specific configurations.

To get started, open your command line and navigate to the directory
where you want to store your code. Then, execute the following command:

.. code-block:: sh

    $ cd your_chosen_directory
    $ django-admin startproject mysite

For more detailed instructions, you can refer to the `Django documentation <https://docs.djangoproject.com/en/4.0/intro/tutorial01/>`_

This command will create a new project directory.
We will continue using the mysite example in the following steps. Naturally, i
n your case, you will need to customize the project name as per your requirements.

::

    └─ your_chosen_directory/
       └─ mysite/
          ├─ manage.py
          └─ mysite/
             ├─ __init__.py
             ├─ settings.py
             ├─ urls.py
             ├─ asgi.py
             └─ wsgi.py


Setup SDC in project
********************

To include SDC in your project
you'll need to install *SDC* and add *sdc_core* to the
to the *INSTALLED_APPS* section in django's *settings.py*.

.. code-block:: python

    ...

    INSTALLED_APPS = [
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'sdc_core',
    ]

    ...

*./mysite/mysite/settings.py*

Finally, from the command line, **cd** into the project directory *mysite* and run the following command:

.. code-block:: sh

    $ cd .mysite
    $ python ./manage.py sdc_init


This process renames settings.py to base_settings.py and creates a new settings.py file.
The new settings.py imports base_settings.py and extends it with additional configuration. Specifically, it:

- Adds four new Django modules to INSTALLED_APPS
- Ensures the template settings are correctly configured
- Adjusts the static files directory settings
- Sets key properties for SDC:
    - SERVER_CALL_VIA_WEB_SOCKET = False
    - MODEL_FORM_TEMPLATE = "elements/form.html"
    - LOGIN_CONTROLLER = "sdc-login"
    - LOGIN_SUCCESS = "/"

Additionally, it includes the following folders and files:

::

    └─ your_chosen_directory/
       └─ mysite/
          ├─ template/
             ├─ elements
                ├─ form.html
                └─ inline_form.html
             ├─ base.html
             └─ index.html
          ├─ Assets/
             └─ ...
          ├─ manage.py
          └─ mysite/
             ├─ routing.py
             ├─ base_settings.py
             └─ ...



The changes include all server-side modifications.
All changes in the Asserts folder have been skipped here
for the moment. In the following the client side modifications are presented.

The SDC client
**************

The whole client is organized in the *Assets* directory

::

    └─ ...
       ├─ Assets/
          ├─ src/
             ├─ sdc_tools/
                └─ ...
             ├─ sdc_user/
                └─ ...
             ├─ index.organizer.js
             └─ index.style.scss
          ├─ webpack.config/
             ├─ webpack.development.config.js
             ├─ webpack.production.config.js
             └─ webpack.default.config.js
          ├─ babel.config.json
          └─ gulpfile.js
       ├─ package.json
       └─ ...

Let's first look at the dependencies in the package.json
file. The following list presents all the development dependencies.

.. include:: snippets/js_dev_deps.rst

All development dependencies are necessary for the build process.
The remaining dependencies need to be installed for the error-free application of SDC

.. include:: snippets/js_deps.rst

Please run the following to initialize the client.

.. code-block:: sh

    $ npm install

And you are done!!