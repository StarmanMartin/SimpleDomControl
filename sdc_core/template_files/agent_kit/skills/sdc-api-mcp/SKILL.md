---
name: sdc-api-mcp
description: SimpleDomControl (SDC) REST API, API tokens and the MCP endpoint — use when exposing data to scripts or AI clients, creating or revoking API tokens, choosing privileges, enabling or configuring MCP (SDC_MCP), or calling sdc_api/ or sdc_mcp/.
---

# REST API, API tokens and MCP

Both channels use the SdcModels with their own rules (`is_authorised` / `get_queryset`) plus the **privileges of
an API token**, which only narrow what the token's user may do.

## API tokens

```
python manage.py sdc_tokens create --user admin --name "report script" --privileges "model:Book:read" [--days 30]
python manage.py sdc_tokens list [--user admin] [--all]
python manage.py sdc_tokens revoke <prefix or id>
```

The token (`sdc_…`) is printed once (last output line); only its hash is stored. Users manage their own tokens on
the page `/~sdc-api-tokens`.

| Privilege | Allows |
|---|---|
| `model:<Model>:read` / `:write` / `:delete` | read; create and change; delete records of one model (`write` does not include `read`) |
| `model:*:read` / `:write` / `:delete` | the same for all models |
| `account:read`, `account:write`, `account:tokens` | own user record and token list; own profile (never password, e-mail, username); create/revoke own tokens |

Presets for `--privileges`: `read` (`model:*:read`, `account:read`), `read_write`, `full`.
Lifetimes: `SDC_API_TOKENS` in `settings.py` (`max_lifetime_days`, `default_lifetime_days`).

## REST API (`/sdc_api/`)

`Authorization: Bearer sdc_…` on every request. `GET|POST /sdc_api/<model>/`, `GET|PUT|PATCH|DELETE
/sdc_api/<model>/<id>/` (forms of `SdcMeta`; list filters as query string, `?_fields=a,b` for fewer fields),
`/sdc_api/account/`,
`/sdc_api/tokens/`, `POST /sdc_api/login/` (username + password → short-lived token). Missing privilege → 403 with
`privilege`. Description: `python manage.py sdc_open_api` → `openapi.generated.yaml`.

## MCP endpoint (`/sdc_mcp/`)

Enable in `settings.py`:

```python
SDC_MCP = {
    'enabled': True,
    'models': ['Book'],     # or '__all__'; SdcMeta.mcp = False always hides a model
    'max_records': 50,
}
```

`python manage.py sdc_mcp_config --user admin --privileges read` prints the `claude mcp add …` command and an
`.mcp.json` entry and creates the token. Tools per token: `model_load`, `model_get` (read privilege; both take
`fields`),
`<model>_create` / `<model>_update` (write), `<model>_delete` (delete), `account_get` / `account_update`,
`describe` (with `sdc_teach` data). Resources: `sdc://skill`, `sdc://skill/<app>`, `sdc://openapi`.

Check quickly with the Django test client (no server needed):

```python
from django.test import Client
Client(headers={'Authorization': f'Bearer {token}'}).post(
    '/sdc_mcp/', '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}', content_type='application/json')
```
