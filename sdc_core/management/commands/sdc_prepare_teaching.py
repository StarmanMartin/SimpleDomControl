import inspect
import os

from django.core.management.base import BaseCommand

from sdc_core.management.commands.init_add import options
from sdc_core.management.commands.utils.teach_controllers import controller_line, sdc_controllers
from sdc_core.management.commands.utils.teach_models import is_editable, sdc_models

GUIDE = '''# Prepare this SimpleDomControl project for `sdc_teach`

`python manage.py sdc_teach` crawls the web UI in a headless browser and writes `SDC_SKILL.md`, a skill
file that tells AI agents how to operate the app. It records automatically:

- the navigation tree (`/~view~child` paths), view arguments with example values and required URL params,
- every link, every button with its handler and observed effect, every form with its fields,
- server calls and all SdcModel WebSocket messages, per controller,
- for each controller its app, server view class and Django URL.

What the crawler cannot see is *meaning*: what a view is for, what a record represents, what the
destructive actions do (delete/save/submit/logout are never clicked), and who may do what. That comes from
the documentation of SDC models and controllers, which `sdc_teach` copies **verbatim** into the skill file:

- SDC model → the class docstring, under `## Data models` → `### <ModelName>`.
- Controller → the JSDoc block above the client class, under `## Controllers` → `### <tag-name>`.

Your task: write this documentation for the items listed at the end of this prompt.

## Rules for all documentation

- Read the code first: the model class (fields, `SdcMeta`, `is_authorised`, `get_queryset`), the server
  view in `<app>/sdc_views.py`, the client controller JS and its template in
  `<app>/templates/<app>/sdc/<name>.html`. Only document what the code does; never invent behaviour.
- Write for an agent that operates the UI, not for a developer reading the code: purpose, meaning,
  preconditions and effects. No implementation details (no method internals, no CSS classes).
- Do not repeat what the crawler already records (lists of links/buttons/fields, URLs, the server view).
  Mention a button or field only to explain what it means or what it does when the crawler cannot find out.
- Plain Markdown, English, 3–12 lines. First line: one sentence summary. No headings (the skill file
  already uses `#`–`###`), no JSDoc tags such as `@param`, no HTML.
- Use `backticks` for model names, field names, controller tags, argument names and literal values.

## SDC model docstrings

Where: the first statement of the model class, as triple-quoted string.

```python
class Book(models.Model, SdcModel):
    """
    A book in the library catalogue; one record per edition.

    - `title`, `isbn` (unique), `published` (date); `author` → `Author`.
    - `status`: `available`, `lent` or `lost`; only staff can set `lost`.
    - Readable by every logged-in user; created/edited by staff only (`is_authorised`).
    - Deleting a book also deletes its `BookContent` rows.
    - Shown in `<book-list>`, edited in `<book-edit>`.
    """
```

Cover: what one record represents, the important fields with their meaning/units/allowed values, relations
to other models, who may read/create/edit/delete it (in words, from `is_authorised` / `get_queryset`),
side effects (emails, cascades, computed fields) and which controllers show or edit it.

## Controller JSDoc

Where: a `/** ... */` block directly above `class <Name>Controller extends AbstractSDC` in the controller
JS file (only blank lines in between). Never write `*/` inside the text.

```js
/**
 * Edit form for one `Book`; opens in the detail area of `<main-view>`.
 *
 * - Arguments: `pk` (required) is the id of the book to edit.
 * - "Save" stores the changes via the model socket and returns to `<book-list>`.
 * - "Delete" removes the book after a confirm dialog; this cannot be undone.
 * - Requires a logged-in staff user, otherwise `sdc-error 403` is shown.
 */
class BookEditController extends AbstractSDC {
```

Cover: what the user sees and can do there, how to reach it and which arguments it needs (and what they
mean), what the important actions do (especially delete/save/submit/logout, which the crawler skips),
required login or permissions, and which models it shows or changes. For small embedded helper controllers
(buttons, widgets) one or two sentences are enough.

## When you are done

1. Run `python manage.py sdc_prepare_teaching` again; the list below must be empty.
2. Run `python manage.py sdc_teach --no-ask` to regenerate `SDC_SKILL.md` (`--no-ask`: the command would
   otherwise ask in the terminal for missing documentation). Add `--user <name> --password <pw>` to also
   crawl the logged-in UI.
'''


class Command(BaseCommand):
    help = ('Prints a prompt for an AI agent explaining how to document SDC models and controllers so that '
            'sdc_teach produces a good skill file, followed by the list of undocumented models and controllers.')

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true',
                            help='Also list documented models and controllers with their current text (to review them)')

    def handle(self, *args, **ops):
        root = options.PROJECT_ROOT
        models = [m for m in sdc_models() if is_editable(m['file'], root) and (ops['all'] or not m['doc'])]
        controllers = {t: c for t, c in sorted(sdc_controllers().items())
                       if is_editable(c['file'], root) and (ops['all'] or not c['doc'])}

        lines = [GUIDE, f'## {"All" if ops["all"] else "Undocumented"} models and controllers', '']
        if not models and not controllers:
            lines.append('Nothing to do: every SDC model and controller of the project is documented.')
        for m in models:
            lines.append(f'- Model `{m["name"]}` ({m["app"]}): '
                         f'{os.path.relpath(m["file"], root)}:{inspect.getsourcelines(m["model"])[1]}')
            lines += self._current(m['doc'])
        for tag, c in controllers.items():
            lines.append(f'- Controller `<{tag}>` ({c["app"]}): {os.path.relpath(c["file"], root)}:'
                         f'{controller_line(c["file"], tag)}, server view `{c["view_class"]}`')
            lines += self._current(c['doc'])
        self.stdout.write('\n'.join(lines))

    @staticmethod
    def _current(doc):
        if not doc:
            return []
        return ['  Current documentation:'] + [f'  > {l}'.rstrip() for l in doc.splitlines()]
