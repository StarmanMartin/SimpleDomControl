# SDC roadmap

Larger projects of SimpleDomControl (server) and SimpleDomControlClient. Each project has a plan in this directory
with milestones (M) and work packages (WP); the plan records the decisions, the status and where the
implementation differs from the text. Small fixes go to `ISSUES.md` (workspace root), released changes to
`CHANGELOG.md`.

## Projects

| Project | Plan | Status | Version |
|---|---|---|---|
| API tokens with privileges and MCP endpoint | [mcp.plan.md](mcp.plan.md) | M1–M5 done; M6 open (optional) | 0.163.0 |
| Fewer tokens for AI agents (scripts, skills, benchmark) | [agents.plan.md](agents.plan.md), [agents.architecture.md](agents.architecture.md) | M0 done (baseline 17/18, 10.4M input tokens, 7.65 USD); M1 next | — |

## Next steps (in order)

1. **Publish 0.163.0** — push `master` of both repos, publish to PyPI and npm. Before that, run `yarn install` in
   `SimpleDomControl` (the `yarn.lock` for 0.163.0 is not committed yet). Breaking for REST API clients:
   `POST sdc_api/login/` returns no `refresh_token` any more (see CHANGELOG, "Upgrade").
2. **Fewer tokens for AI agents** — D1–D5 accepted as proposed:
   - M0 baseline benchmark: done ([report](agents-bench/2026-11-11-baseline.md))
   - M1 `manage.py sdc_agent` scripts (start with WP1.1: no command prompts any more)
   - M2 agent kit (`AGENTS.md` + skills in every project), M3 measure and tune, M4 runtime follow-ups, M5 release
3. **Remove the deprecated JWTs** (release after 0.163.0) — `SDC_API_TOKENS['accept_jwt']`, the JWT path of
   `api_tokens.authenticate` and the refresh flow of `sdc_api/login/`; `jwt_utils.py` stays for the e-mail links of
   `sdc_user` (or moves there). See mcp.plan.md, WP2.6.

## Later (not planned in detail)

From mcp.plan.md, M6:
- OAuth 2.1 for MCP clients that only support OAuth (tokens stay `ApiToken`s)
- Rate limiting per token
- Server calls of `SDCView`s as MCP tools (`call:<view>` privilege)
- File fields over REST/MCP tools
- MCP bridge to the open browser page (`navigate`, `read_page`, `fill_form`, `click`)
- Audit log per token

## Conventions for plans

- File name `<topic>.plan.md`; one row in the table above.
- Sections: goal, current state, decisions (D…), milestones with exit criteria, work packages, dependencies, risks.
- When a milestone is finished, mark its heading **done** and add a short status: what was built, where, and
  where it differs from the plan.
