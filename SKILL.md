---
name: task-board
description: Use when reading or changing tasks on the holdingxs board.
---

# Task board

A personal task board at `https://dev.holdingxs.xyz`. You read and write it over
an HTTP API with a bearer token; there is no other copy to keep in sync.

## When to use

- The user says what they worked on, paused, or finished.
- A task should be added, re-statused, have steps ticked, or be removed.
- The user asks what is on the board, or what has gone stale.

## Auth

One token per account, sent as `Authorization: Bearer <token>`. Set it once:

```bash
export HX_TOKEN="…"          # in the shell profile, or a secret the agent can read
export HX_BASE="https://dev.holdingxs.xyz"   # default; only set if different
```

Never print the token, echo it, or write it into a file that gets committed.
The user issues and revokes it in the board's Account dialog. **The token covers
`/api/tasks` only** — `/api/me`, `/api/account/*` and `/api/auth/*` want a
browser session, so a 401 there proves nothing about the token. Test the token
with `GET /api/tasks`.

## Use the helper, not raw curl

`scripts/tb.py` (Python 3 stdlib, no dependencies) does the whole contract:

```bash
python3 scripts/tb.py list
python3 scripts/tb.py list --json
python3 scripts/tb.py show reading
python3 scripts/tb.py add "ATAS notes" --status in_progress --note "protocol notes first"
python3 scripts/tb.py set reading --status done --tick 2
python3 scripts/tb.py set reading --add-step "check the appendix"
python3 scripts/tb.py rm reading
```

Plain HTTP, if you prefer (`references/api.md` has the full contract):

```
GET    /api/tasks               the whole board, newest update first
POST   /api/tasks               {title, note, status, next, steps} -> 201 + the task
PATCH  /api/tasks/<id>          any subset of those fields
DELETE /api/tasks/<id>          final, no undo
```

## How to write

1. **Read first.** `tb list` so you patch the existing row instead of making a
   near-duplicate. Titles are not unique.
2. Change the least that says what happened. Keep the user's own words in
   `title` and `note`; do not pad the note with a summary they did not write.
3. **Read it back** and report what you saw — status, `updated`, step count. A
   `201` is not proof the board says what you meant.

`status` is one of `in_progress`, `on_hold`, `planned` (`done` closes it).
`steps` is `[{"done": true, "text": "…"}, …]` and is **replaced as a whole** —
always read the array, edit it, send the whole thing back. `updated` is set by
the server; never send it. Ids are ASCII slugs derived from the title (a
non-ASCII title becomes `task-<hash8>`); URL-encode them in a path.

## Gotchas

- **Cloudflare 403 `error code: 1010`** means the client looked like a script.
  Send a browser-like `User-Agent` on every call. `tb.py` does; hand-rolled curl
  needs `-A`.
- `PATCH` with no recognised field → `400 nothing to update`.
- `DELETE` and `PATCH` on a missing id → `404 task not found`.
- `steps` shown in the UI are the task's **Progress** bar. Do not invent steps
  or a checklist the user did not ask for.
- The ledger (`/api/ledger`) is a different thing: four daily marks, not tasks.
  Leave it alone unless asked.

## Test prompts

| Say this | Expect |
|---|---|
| "add a task for the ATAS notes, in progress" | reads the board, POSTs, reads the row back |
| "mark the reading task done and tick its last step" | PATCH with the status and the whole steps array, then verify |
| "what's stale?" | lists open tasks with old `updated` dates, no writes |
