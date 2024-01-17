.. _sdc-controller-label:

SDC controller
==============

A controller has two parts a client and a server. This is preceded by a short chapter on generating a controller.
This is followed by a paragraph on how the
server code is to be understood. This is followed by a short
overview of the client code (HTML, SCSS, JavaScript)

.. _new-controller-controller:

New controller
--------------

We recommend delegating the creation of controllers to the provided scripts designed for this purpose.
To initiate the creation of a new controller, execute the following command within the project directory:

.. code-block:: sh

    $ python manage.py sdc_cc

To complete the process, you will be prompted with two questions in the terminal. Firstly,
specify the Django app in which the controller should be created (for example, *mypage*).
Secondly, provide a name for the new controller (in this example, the name is about_me).
It's important to note that only snake case should be used for the controller name. For additional details, refer to :ref:`sdc-cc-core`.

Alternative können die fragen auch übergangen werden.


.. code-block:: sh

    $ python manage.py sdc_cc -a <django_app_name> -c <sdc_controller_name>

Jedoch muss der *sdc_controller_name* im **snake_case** angegeben werden. Wenn die django app nicht in den
settings angegeben ist wir der angegeben parameter ignoriert.



Server part
-----------

A controller on the client side consists usually of three Files. A HTML template file a SCSS style file and the JavaScript code File.
The JavaScript contains the controller class which ha a *contentUrl* property. This url points at a entrypoint which is registered at the *sdc_url.py* file. This file
will be generted automaticly when the first controller in the coresponding Django app is generted. The registered url then calls python ViewClass.
This Class extents *sdc_core.sdc_extentions.views.SDCView*. This Class is closely related
to the *django.views.View* class. Additionally to the standard handler get, post, put etc. it also has the *get_content* handler. This method gets called only to
render and serv the template.

For the following example let us assume that we have a django project called *mysite* with an app called *myapp*.


.. code-block:: python

    ...
    urlpatterns = [
        # scd view below
        ...
        path('main_view', sdc_views.MainView.as_view(), name='scd_view_main_view'),
        ...
    ]
    ...

*./mysite/myapp/sdc_urls.py*

.. code-block:: python

    ...
    class MainView(SDCView):
        template_name='main_test/sdc/main_view.html'

        def get_content(self, request, *args, **kwargs):
            return render(request, self.template_name)
    ...

*./mysite/myapp/sdc_views.py*

.. code-block:: js

    ...
    class MainViewController extends AbstractSDC {

        constructor() {
            super();
            this.contentUrl = "/sdc_view/main_test/main_view"; //<main-view></main-view>

    ...

*./Assets/src/myapp/controller/main_view/main_view.js*

To be able to work with this construct usfully it is nessesary to parameterize the query. Therefore you can either add url parameter in the *sdc_urls.py*


.. code-block:: python

    ...
    urlpatterns = [
        # scd view below
        ...
        path('main_view/<int:pk>', sdc_views.MainView.as_view(), name='scd_view_main_view'),
        ...
    ]
    ...

*./mysite/myapp/sdc_urls.py*

If you then run:

.. code-block:: sh

    $ python manage.py sdc_update_urls

the client will be automaticlly updetad its *contentUrl*

.. code-block:: js

    ...
    class MainViewController extends AbstractSDC {

        constructor() {
            super();
            this.contentUrl = "/sdc_view/main_test/main_view/%(pk)s"; //<main-view data-pk=""></main-view>

Error handling and Permissions
______________________________

