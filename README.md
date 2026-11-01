# task-board skill

An agent skill for reading and writing tasks on a personal task board over its
HTTP API. Point it at the board, give it a token, and it can list, add, update
and delete tasks.

```
SKILL.md              when to use it, the rules, the gotchas
references/api.md     every endpoint, the payloads, the error codes
scripts/tb.py         the client — Python 3 stdlib, no dependencies
```

## Use it

Drop the folder into wherever your agent keeps skills (usually
`~/.claude/skills/`, `~/.codex/skills/`, or the agent's own skills directory),
then give the agent the token:

```bash
export HX_TOKEN="…"                          # from the board's Account dialog
export HX_BASE="https://dev.holdingxs.xyz"   # the default, if your board is elsewhere
```

Check it works before handing the agent a task:

```bash
python3 scripts/tb.py list
```

## What it covers

| | |
|---|---|
| `GET /api/tasks` | the whole board |
| `POST /api/tasks` | add one — title, note, status, next date, steps |
| `PATCH /api/tasks/<id>` | change any subset of those |
| `DELETE /api/tasks/<id>` | remove one, final |

The interesting parts are the failure modes, and they are written down:
Cloudflare answers `403 error code: 1010` to clients with a script-like
`User-Agent`; `steps` is replaced as a whole, never per item; `PATCH` with no
recognised field returns `400 nothing to update`; the token reaches `/api/tasks`
and nothing else, so a 401 from `/api/me` means nothing.

No credentials live in this repo. The token is read from the environment.
