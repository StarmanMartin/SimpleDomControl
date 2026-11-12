---
name: sdc-model
description: SimpleDomControl (SDC) data models — use when adding or changing an SdcModel, its fields, SdcMeta forms (create_form, edit_form), permissions (is_authorised, get_queryset), validation, migrations, list or detail templates, or when reading and saving records in a client controller (querySet, SdcQuerySet).
---

# SDC models

An SdcModel is a Django model plus the `SdcModel` mixin. The same rules serve the browser (model WebSocket), the
REST API (`sdc_api/`) and MCP (`sdc_mcp/`).

```
python manage.py sdc_agent new-model <app> Review       # model, form, list/detail templates
python manage.py sdc_agent where Review --show          # files and code of an existing model
python manage.py makemigrations && python manage.py migrate
```

## Server

```python
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from sdc_core.sdc_extentions.models import SdcModel


class Review(models.Model, SdcModel):
    """A rating of one `Book` (1–5) with an optional comment. Logged-in users create reviews; …"""
    book = models.ForeignKey('library.Book', on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)

    class SdcMeta:
        create_form = "library.forms.ReviewForm"    # dotted path (or the class)
        edit_form = "library.forms.ReviewForm"
        fields = "__all__"                          # fields sent to clients; or a list; `exclude` hides fields
        # html_list_template / html_detail_template: templates of <sdc-list-view> / <sdc-detail-view>
        # mcp = False                               # never expose this model over MCP

    @classmethod
    def is_authorised(cls, user, action, obj):
        # action: connect, load, list_view, detail_view, edit_form, create_form, save, create, upload, delete
        return user.is_authenticated

    @classmethod
    def get_queryset(cls, user, action, obj):
        return cls.objects.all()                    # rows this user may reach for this action
```

- **`sdc_agent new-model` writes `is_authorised` returning `False`**: nothing is allowed until you change it.
- Forms are plain Django `ModelForm`s in `<app>/forms.py`; validation (validators on the model, `clean_<field>`)
  applies everywhere the model is saved. More named forms: any other `SdcMeta` attribute with a form path
  (`short_form = "…"`), used with `form_name`.
- Write the docstring as shown (what the model is, who may do what): the AI assistant and MCP read it.

## UI without own controllers

The bundled controllers work for every SdcModel (permissions apply):

- list: `/~sdc-list-view~&model=Review` (live list with edit/detail/remove)
- create: `/~sdc-model-form~&model=Review`; edit: `/~sdc-model-form~&model=Review&pk=3` (saves on change)
- detail: `/~sdc-detail-view~&model=Review&pk=3`
- in a template: `<sdc-model-form data-model="Review" data-pk="3"></sdc-model-form>`

## Client

The asset build (`python manage.py sdc_agent build`) generates and registers a JS class per SdcModel
(`Assets/src/models/`, via `sdc_make_model_js`); rebuild after adding a model or field.

```js
// in a controller method
const reviews = this.querySet('Review', {book: this.bookId});   // filter: Django field lookups
reviews.on_update = () => this.refresh();                      // live updates from the server
return reviews.load().then(() => {
    for (const review of reviews) { console.log(review.id, review.rating); }
});

this.querySet('Review').create({book: 1, rating: 4});           // returns a promise
```

Queryset: `load(filter, {limit})`, `get(filter)`, `byId(id)`, iteration, `length`, `new(values)`,
`create(values)`, `save({pk, data})`, `delete({pk})`, `setFilter` / `addFilter`, callbacks `on_update`,
`on_create`. Records: fields as properties, `id`, `toJson()`.
