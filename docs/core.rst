Core of SDC
===========

The *SDC* package, which consists of three Django apps:
*sdc_core*, *sdc_tools*, and *sdc_user*. The *sdc_core* Django app serves as the foundation of
*SDC*. It encompasses essential components such as management command scripts and a *consumer.py*,
which acts as a handler for all *SDC* websocket requests. Additionally, the *sdc_core* app houses a
Python package named *sdc_extensions*.


Management command
------------------

The commands provided by *SDC* are yous to simplify the Development. It allows to create controller and models as well as updating the urls.
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

The command *sdc_cc* creates a new SDC controller. A short introduction can be found here: :ref:`new-controller-controller`.
Make sure that you are in the same directory as the *manage.py* and run:

.. code-block:: sh

    $ python manage.py sdc_cc

You will need two answer two questions in the terminal to finish the process.
Firstly, it needs to know in witch Django app (we choose  *mypage* in the example below)
the controller has to be created. Secondly, you have to give the new controller a name
(in the example the name is *about_me*). Importante, only use snake case for the controller
name. See  for more details.

.. code-block:: sh

    Enter number to select a Django app:
    1 -> mypage
    2 -> ...
    Enter number: [2] 1
    Enter the name of the new controller (use snake_case): about_me


3 - sdc_update_url
******************

The *sdc_update_url* updated the *contentUrl* property of the sdc controller.
This command is only needed if you change the auto generated path in the *sdc_urls.py*
files manually. For example let us a numeric parameter to the url path of the about me controller.

.. code-block:: diff

    +from django.conf.urls import url
     ...
     urlpatterns = [
        # scd view below
    -   path('about_me', sdc_views.AboutMe.as_view(), name='scd_view_about_me'),
    +   url('about_me/(?P<key>[0-9]{1,20})', sdc_views.AboutMe.as_view(), name='scd_view_about_me'),
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

    -       this.contentUrl = '/sdc_view/main_view/about_me';    //<about-me></about-me>
    +       this.contentUrl = '/sdc_view/main_view/about_me/%(key)s'; //<about-me data-key=""></about-me>
    ...

*mysite/mypage/static/mypage/js/sdc/about_me.js*

4 - sdc_update_links
********************

The *sdc_update_links* command organizes client files by rearranging them. All client files are typically organized within their respective Django apps. However, for the sake of convenience, all client-related files are also linked in a global Asset directory. This directory also contains all build scripts for the client.

5 - sdc_get_model_infos
***********************

The *sdc_get_model_infos* command returns a JSON object containing all the necessary information for IDEs to connect with all files related to a certain model.

6 - sdc_get_controller_infos
****************************

The *sdc_get_controller_infos* command returns a JSON object containing all the necessary information for IDEs to connect with all files related to a certain sdc-controller.

SDC extensions
--------------