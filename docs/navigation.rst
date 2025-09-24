.. _sdc-how-to-nav:

How to navigate?
================

The SDC navigation controller should be the first controller in the index HTML page.
This controller enables dynamic navigation between your controller views.

Basic Navigation
----------------

.. include:: basic_navigation.rst

Parametrized Navigation
-----------------------

There are two types of parameters that can be passed to the subsequent controller. Parameters that are intended for
the Python server view class and parameters that are to be passed directly to the JS SDC controller.

To pass parameters to the client, you can use the onInit method of the controller. This is part of: :ref:`sdc-controller-label-live`.
To address these, you must write the parameters in the link separated by ‘&’ after the ‘?’. For example:

.. code-block:: html

    <a class="navigation-links" href="/view-a/view-b?name=Max&age=3"

And in the *ViewA* Controller the matching counterpart with:

.. code-block:: JavaScript

    function ClassA() {
        ...
        onInit(name, age) {
        ...
    }

To pass parameters to the server, add the necessary parameters to the relevant URL path in the sdc_url.py file, as well as to the SDCView class, as shown below.

.. code-block:: python

    ...
    urlpatterns = [
        path('view-a/<int:age>', sdc_views.ViewA.as_view(), name='scd_view_view_a'),
    ]
    ...

*./root_dir/app/sdc_urls.py*

and

.. code-block:: python

    ...
    class ViewA(SDCView):
        template_name = 'app/sdc/view_a.html'

        def get_content(self, request, age, *args, **kwargs):
            return render(request, self.template_name, {'age': age})
    ...

*./root_dir/app/sdc_views.py*

Then, from the project root directory, you need to run 'sdc_update_url'. This command updates the URL path in the SDC controller.

.. code-block:: sh

    ./manage.py sdc_update_url


Navigate from code
-------------------

You can navigate to a divergent SDC controller from the JS code at any moment. Therefore, you only need to import the trigger and call it.
as follows:

.. code-block:: JavaScript

    import {AbstractSDC, app, trigger} from 'sdc_client';
    ...
    class ViewA(AbstractSDC) {
        ...
        sameHandler() {
            const age = 3;
            const name = 'Max';
            trigger('goTo', ['view-a', 'view-b'], {age, name});
        }
    }

Subview in Modal
----------------

If the *sdc_detail_view* has an additional data attribute of *data-modal* set to a valid css selector of the Modal DOM, the SDC Navigation controller
will find the closest BS Modal and open it. It then sets the new view within the modal.


.. code-block:: HTML


    <!-- Modal -->
    <div class="modal fade" id="exampleModal" tabindex="-1" aria-labelledby="exampleModalLabel" aria-hidden="true">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="sdc_detail_view" data-modal="#exampleModal">
        </div>
      </div>
    </div>