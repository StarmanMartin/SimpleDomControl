Core of SDC
===========

The *SDC* package, which consists of three Django apps:
*sdc_core*, *sdc_tools*, and *sdc_user*. The *sdc_core* Django app serves as the foundation of
*SDC*. It encompasses essential components such as management command scripts and a *consumer.py*,
which acts as a handler for all *SDC* websocket requests. Additionally, the *sdc_core* app houses a
Python package named *sdc_extentions* (this spelling is the real package name,
e.g. ``from sdc_core.sdc_extentions.views import SDCView``).


Management command
------------------

The commands provided by *SDC* simplify development. They create controllers and models and update the URLs.
Let us first list all important commands:

.. code-block:: sh

    # Initialize a new SDC project
    $ python manage.py sdc_init
    # Create a new controller
    $ python manage.py sdc_cc
    # Create a new SDC model
    $ python manage.py sdc_new_model


A brief summary of the terminal commands:

.. _sdc-init-core:

1 - sdc_init
************

The command *sdc_init* initializes SDC in your project. The *sdc_init* command has been introduced in :ref:`getting-started-label`.

.. code-block:: sh

    $ python manage.py sdc_init

.. _sdc-cc-core:

2 - sdc_cc
**********

The command *sdc_cc* creates a new SDC controller. A short introduction can be found here: :ref:`sdc-controller-label`.
Make sure that you are in the same directory as the *manage.py* and run:

.. code-block:: sh

    $ python manage.py sdc_cc

The command asks three questions in the terminal. Firstly, it needs to know in
which Django app the controller has to be created (we choose *mypage* in the
example below; the project package is also listed). Secondly, you have to give
the new controller a name (in the example the name is *about_me*). Important:
only use snake_case for the controller name. Thirdly, you can select
controllers to add as mixins. In a terminal, the app and mixin questions are
interactive selection lists. See :ref:`sdc-controller-label` for more details.

The questions can be answered with options instead:

.. code-block:: sh

    $ python manage.py sdc_cc -a mypage -c about_me -m
    $ python manage.py sdc_cc -a mypage -c about_me -m sdc_auto_submit,sdc_update_on_change

``-a`` selects the app and ``-c`` sets the controller name. ``-m`` takes a
comma-separated list of mixin controllers in snake_case; a bare ``-m`` adds no
mixins and skips the question.

.. _sdc-new_model-core:

3 - sdc_new_model
*****************

The command *sdc_new_model* creates a new SDC Model. A short introduction can be found here: :ref:`sdc-model-label`.
Make sure that you are in the same directory as the *manage.py* and run:

.. code-block:: sh

    $ python manage.py sdc_new_model

The command asks two questions in the terminal. Firstly, it needs to know in
which Django app the model has to be created (we choose *mypage* in the example
below). Secondly, you have to give the new model a name (in the example the
name is *BookCover*). Important: only use CamelCase for the model name. See
:ref:`sdc-model-label` for more details.

The questions can be answered with options instead:

.. code-block:: sh

    $ python manage.py sdc_new_model -a mypage -m BookCover


4 - sdc_update_url
******************

The *sdc_update_url* command updates the *contentUrl* property of the SDC controllers.
This command is only needed if you change the auto-generated path in the *sdc_urls.py*
files manually. For example, let us add a numeric parameter to the URL path of the about me controller.

.. code-block:: diff

     ...
     urlpatterns = [
        # scd view below
    -   path('about_me', sdc_views.AboutMe.as_view(), name='scd_view_mypage_about_me'),
    +   path('about_me/<int:key>', sdc_views.AboutMe.as_view(), name='scd_view_mypage_about_me'),
     ]
     ...

*mysite/mypage/sdc_urls.py*


In this case the auto generated url to get the html of the controller would no longer be valid. To update the url simply run:

.. code-block:: sh

    $ python manage.py sdc_update_url

It automatically checks the content URL paths of each controller. If a path has changed, it updates the controller's *content_url*. The resulting changes in the controller are presented below:

.. code-block:: diff

    ...
    class AboutMeController extends AbstractSDC {

        constructor() {
            super();

    -       this.contentUrl = "/sdc_view/mypage/about_me"; //<about-me></about-me>
    +       this.contentUrl = "/sdc_view/mypage/about_me/%(key)s"; //<about-me data-key=""></about-me>
    ...

*mysite/mypage/Assets/src/mypage/controller/about_me/about_me.js*

5 - sdc_update_links
********************

The *sdc_update_links* command organizes client files by rearranging them. All client files are typically organized within their respective Django apps. However, for the sake of convenience, all client-related files are also linked in a global Asset directory. This directory also contains all build scripts for the client.

6 - sdc_get_model_infos
***********************

The *sdc_get_model_infos* command returns a JSON object containing all the necessary information for IDEs to connect with all files related to a certain model.

7 - sdc_get_controller_infos
****************************

The *sdc_get_controller_infos* command returns a JSON object containing all the necessary information for IDEs to connect with all files related to a certain sdc-controller.

SDC extensions
--------------

ToDo