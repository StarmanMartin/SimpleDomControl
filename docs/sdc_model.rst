.. _sdc-model-label:

SDC model
=========

Thanks to a sophisticated ORM system (Object–Relational Mapper), the models in Django enable simple database development.
Thanks to the SDC extension, these models can also be used on the client side via a WebSockets-based system.
All SDC models are generated with forms for creation and editing. The models also include a list and detail view.
However, these are purely HTML-based and can only be used for the browser application.


.. _new-model-label:

New model
---------

We recommend delegating the creation of Models to the provided scripts designed for this purpose.
To initiate the creation of a new Model, execute the following command within the project directory:

.. code-block:: sh

    $ python manage.py sdc_new_model

To complete the process, respond to two prompts in the terminal. First, specify the Django app
in which the controller should be created (e.g., *main_app*). Second, provide a name for the new Model
(for example, *Books*). It's important to note that only CamelCase should be used for the Model name.
For additional details, refer to :ref:`sdc-new_model-core`.

Alternatively, you can skip the prompts using the following command:


.. code-block:: sh

    $ python manage.py sdc_new_model -a <django_app_name> -c <DjangoModel>

However, the *DjangoModel* must be specified in **CamelCase**. If the Django app is not listed in the installed_apps in the django settings, the provided parameter will be ignored.

Server Model
------------

When a new model is created, only server code is generated initially. This includes a model class and a form class.

.. include:: snippets/book_model.rst

and the from:

.. include:: snippets/book_model_form.rst

The model is created with some properties. First the *_SdcMeta* subclass. The properties can then be accessed
vie the public getter *SdcMeta*

.. code-block:: python

    class _SdcMeta:
        """Meta data information needed to manage all SDC operations."""
        edit_form = "main_app.forms.BookForm"
        create_form = "main_app.forms.BookForm"
        html_list_template = "main_app/models/Book/Book_list.html"
        html_detail_template = "main_app/models/Book/Book_details.html"


- edit_form: The Python import path to the edit/update form class.
  This form is not only used to generate an HTML view, but also serves as an intermediary class for every save operation from the client.
  Hence, only properties handled in this form can be saved from the SDC client.

- create_form: The Python import path to the create form class.
  Like the edit form, it is not just an HTML form, but also acts as an intermediary class for every create operation from the client.

- html_list_template: The template path used to render the list view.
  This template provides an HTML view for displaying a pre-filtered list of model entries. The entries can be server-rendered directly, or, if required, defined dynamically by the client.

- html_detail_template: The template path used to render the detail view.
  This is a simple server-rendered page for displaying a model instance in more detail.


.. code-block:: python

    class SearchForm(AbstractSearchForm):
        """A default search form used in the list view. You can delete it if you dont need it"""
        CHOICES = (("title", "Title"), ("author", "Author"),)
        PLACEHOLDER = "Title or Author"
        DEFAULT_CHOICES = CHOICES[0][0]
        SEARCH_FIELDS = ("title", "author")

The 'SearchForm' property is used in the list view. It enables users to filter the list of elements and search for items.
The Search Form is used in the SDC-search-view and filters the List View it is included in.


- CHOICES: is a list of tuples. Each element is selectable sort key. The first entry in the tuple is the property name th4 second the Human readable name.

- PLACEHOLDER: is the placeholder in the search input.

- DEFAULT_CHOICES: is the select default sort filter.

- SEARCH_FIELDS: is the properties included in the search process.

.. code-block:: python

    @classmethod
    def render(cls, template_name, context=None, request=None, using=None):
        if template_name == cls.SdcMeta.html_list_template:
            sf = cls.SearchForm(data=context.get("filter", {}))
            context = context | handle_search_form(context["instances"], sf, range=3)
        return render_to_string(template_name=template_name, context=context, request=request, using=using)


The render methode renders the HTML from the model templates.


On the client side
------------------

Let us assume we have a model called Book. This model has

