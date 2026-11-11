# AGENTS.md

Django project built with **SimpleDomControl (SDC)**. The framework source is installed as a package (Python
`sdc_core`, JavaScript `sdc_client`) and is not part of this project: use the commands and skills below instead
of searching for it.

## How SDC projects are built

- Every UI element is a **controller pair** with one name, e.g. `book_list` ↔ tag `<book-list>`:
  - server: view class `BookList(SDCView)` in `<app>/sdc_views.py`, template `<app>/templates/<app>/sdc/book_list.html`,
    URL in `<app>/sdc_urls.py` (`/sdc_view/<app>/book_list`)
  - client: `<app>/Assets/src/<app>/controller/book_list/book_list.js` (+ `.scss`), imported in
    `<app>/Assets/src/<app>/<app>.organizer.js`
- **SdcModels** (`class Book(models.Model, SdcModel)` with `SdcMeta` forms and `is_authorised` / `get_queryset`) are
  synced to the browser over WebSocket; the REST API (`sdc_api/`) and MCP (`sdc_mcp/`) use the same rules.
- Views are opened by URL path: `/~book-list` (see the `sdc-controller` skill).

## Commands (never interactive, short output)

```
python manage.py sdc_agent overview                  # apps, controllers, models with file:line
python manage.py sdc_agent where <tag|Model>         # every file of one controller or model
python manage.py sdc_agent check                     # problems + fixes; run after every change
python manage.py sdc_agent new-controller <app> <snake_name>
python manage.py sdc_agent new-model <app> <ModelName>
python manage.py sdc_agent test [--js] [label]       # summary only; full log in .sdc_agent/logs/
python manage.py sdc_agent build                     # asset build (needs node_modules)
```

## Rules

- Create controllers and models with the commands above, never by copying files; do not edit
  `Assets/src/index.organizer.js`.
- Event handlers are controller methods (`sdc_click="method"` in the template) or plain `function` values in
  `this.events`. Never use arrow functions as handlers in the constructor: SDC calls handlers on the controller of
  the page, and an arrow function from the constructor keeps the wrong `this`.
- Server calls are view methods `def name(self, channel, **kwargs)`, called with `this.serverCall('name', {...})`.
- Model changes: `python manage.py makemigrations && python manage.py migrate`.
- Do not start servers that keep running (`runserver`, `yarn develop`) unless asked.
- Finish with `python manage.py sdc_agent check` (no errors) and the relevant tests.

## Skills (read the one that matches the task)

| Skill | Use it for |
|---|---|
| `sdc-controller` | views, templates, client controllers, events, server calls, navigation |
| `sdc-model` | SdcModels, forms, permissions, migrations, client querysets |
| `sdc-api-mcp` | REST API, API tokens and privileges, MCP endpoint |
| `sdc-testing` | Django and Jest tests, debugging |
| `sdc-ai-knowledge` | documenting models and controllers for the AI assistant (`sdc_teach`) |

Skill files: `.claude/skills/<name>/SKILL.md`.

<!-- sdc:generated:start (rewritten by `python manage.py sdc_agent kit update`; edit outside this block) -->
<!-- sdc:generated:end -->
