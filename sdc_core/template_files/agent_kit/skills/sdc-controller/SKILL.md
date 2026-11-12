---
name: sdc-controller
description: SimpleDomControl (SDC) controllers — use when creating or changing a view, page, component, template, client controller (AbstractSDC), button or click handler, event, server call (serverCall), navigation link or the organizer of an SDC app, or when a controller shows nothing or does not react.
---

# SDC controllers

A controller is a **pair** with one name: `book_list` (snake_case, server) ↔ `<book-list>` (tag, client).

| Part | File |
|---|---|
| server view | `<app>/sdc_views.py`: `class BookList(SDCView)` |
| URL | `<app>/sdc_urls.py`: `path('book_list', sdc_views.BookList.as_view(), name='scd_view_<app>_book_list')` → `/sdc_view/<app>/book_list` |
| template | `<app>/templates/<app>/sdc/book_list.html` (the HTML of the controller, rendered by the view) |
| client | `<app>/Assets/src/<app>/controller/book_list/book_list.js` and `.scss` |
| registration | `<app>/Assets/src/<app>/<app>.organizer.js`: `import {} from "./controller/book_list/book_list.js";` |

## Create, find, check

```
python manage.py sdc_agent new-controller <app> book_list    # creates all parts above
python manage.py sdc_agent where book-list --show            # every file; --show: with the code
python manage.py sdc_agent check                             # broken pairs, wrong handlers, … with fixes
```

### After `new-controller`

- The generated pair works as it is: the view renders the template, the JS loads it. A page whose content comes
  from the server (`get_content` + template) needs **no JS change**; keep the generated `app.register(…, true|false)`
  line (the second argument only says whether it replaces a controller with the same tag).
- Edit the template in `<app>/templates/<app>/sdc/`; `controller/<name>/<name>.html` next to the JS is a git-ignored
  link to it for editors — do not write to it.

A controller is shown wherever its tag is used (`<book-list></book-list>` in another template) or by URL
`/~book-list` (see `references/navigation.md`). JS/SCSS changes need an asset build
(`python manage.py sdc_agent build`) before they appear in the browser.

## Server view

```python
from django.shortcuts import render
from sdc_core.sdc_extentions.views import SDCView, SdcLoginRequiredMixin


class BookList(SdcLoginRequiredMixin, SDCView):        # mixin optional: login required
    template_name = 'library/sdc/book_list.html'

    def get_content(self, request, *args, **kwargs):     # the HTML of the controller
        from library.models import Book
        return render(request, self.template_name, {'books': Book.objects.all()}), {}

    def count_books(self, channel, **kwargs):             # a server call
        from library.models import Book
        return Book.objects.count()
```

- `get_content` returns `render(...)` or `(html, data)`; `data` (JSON) reaches the client as `onLoad(html, data)`
  and `this.contentData`.
- **Server calls**: any public method `name(self, channel, **kwargs)`; the client sends keyword arguments as JSON.
  `channel` is the request (HTTP) or the WebSocket consumer. The return value (JSON-serializable) is the result
  of the client's promise; a dict with `msg` (and `header`) also shows a message; return
  `{'is_error': True, 'msg': '…'}` (WebSocket) or `send_error(msg='…')` from `sdc_core.sdc_extentions.response`
  (HTTP) for an error message.
- The template is plain Django; load `{% load sdc_filter %}` for form helpers (`|addformclass`, `|addclass:"x"`).

## Client controller

```js
import {AbstractSDC, app, trigger} from 'sdc_client';

class BookListController extends AbstractSDC {
    constructor() {
        super();
        this.contentUrl = "/sdc_view/library/book_list";   // must match the URL of the view
        this.events.unshift({'click': {'.more': function ($el, ev) { this.toggle($el); }}});
    }

    onInit(pk) { this.pk = pk; }            // data-* attributes / URL arguments of the tag
    onLoad($html) { return super.onLoad($html); }
    willShow() { return super.willShow(); }
    onRefresh() { return super.onRefresh(); }

    count_books($btn, ev) {                 // template: <button sdc_click="count_books">
        return this.serverCall('count_books', {}).then((count) => this.find('.book-count').text(count));
    }

    toggle($el) { this.find('.extra').toggleClass('d-none'); }
}

app.register(BookListController);
```

- **Handlers**: `sdc_click="method"` (also `sdc_change`, `sdc_submit`, … for other events) calls
  `method($element, event)` on the controller. In `this.events` use `function` values or method names;
  **an arrow function created in the constructor gets the wrong `this`** (SDC calls handlers on the controller of
  the page, not on the object the constructor ran on). Arrow functions *inside* methods are fine.
- `this.find(selector)` searches inside the controller; `this.refresh()` re-renders it; `this.reload()` fetches its
  HTML from the server again (after data changed on the server).
- `this.serverCall(name, args)` returns a promise with the method's return value.
- Messages: `trigger('pushMsg', header, text)`, `trigger('pushErrorMsg', header, text)`.
- Lifecycle: `constructor → onInit(args) → onLoad(html) → children → willShow() → onRefresh()`, later `onRemove()`.

## When a controller does not work

1. `python manage.py sdc_agent check` — missing organizer import, wrong `contentUrl`, missing template,
   missing `app.register`, arrow handlers in the constructor are all reported with the fix.
2. Nothing appears: the tag is not registered (organizer), the view URL is wrong, or the asset build is old.
3. A click does nothing: wrong `this` (arrow function in the constructor), the selector does not match, or the
   method name in `sdc_click` differs.

More: `references/navigation.md` (URLs, links, arguments).
