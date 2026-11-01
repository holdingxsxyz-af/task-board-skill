# task board API

Base: `https://dev.holdingxs.xyz`. Auth: `Authorization: Bearer <token>`.
Send a browser `User-Agent` — Cloudflare answers `403 error code: 1010` to
clients that look scripted (python-urllib's default UA included).

Every response is JSON. Errors are `{"error": "…"}` with a matching status.

## GET /api/tasks

The whole board for the token's account, ordered `updated DESC, title ASC`.

```json
[
  {
    "id": "atas-notes",
    "title": "ATAS notes",
    "note": "protocol notes first",
    "status": "in_progress",
    "created": "2026-11-01",
    "updated": "2026-11-01",
    "next": "2026-11-05",
    "steps": [{"done": false, "text": "collect the protocol notes"}]
  }
]
```

`next` is a date or `null`. `steps` is always an array (possibly empty).

## POST /api/tasks

```json
{"title": "ATAS notes", "note": "", "status": "in_progress",
 "next": "2026-11-05", "steps": []}
```

- `title` is required and trimmed; an empty title is `400 title required`.
- `status` falls back to `planned` when absent or unrecognised.
- `created` and `updated` are set server-side to today.
- Returns `201` with the stored task.

The id is derived from the title: lowercased, non-alphanumerics collapsed to
single dashes (`"ATAS notes"` → `atas-notes`). A title with no ASCII letters or
digits (e.g. Japanese) becomes `task-<first 8 hex of sha256(title)>`. A
collision gets `-2`, `-3`, …

## PATCH /api/tasks/<id>

Any subset of `title`, `note`, `status`, `next`, `steps`. Fields that are absent
are untouched; `next: null` clears the date. `updated` is always refreshed.

- `400 nothing to update` — none of the recognised fields were sent.
- `404 task not found` — no row with that id for this account.
- Returns `200` with the updated task.

`steps` is a full replacement: read the array, change it, send all of it back.
Sending one step deletes the rest.

## DELETE /api/tasks/<id>

`{"ok": true}`. Immediate and final — the UI's six-second undo is a browser-only
trick. `404` if the id does not exist.

## Status values

| value | meaning in the UI |
|---|---|
| `planned` | Planned |
| `in_progress` | In progress |
| `on_hold` | On hold |
| `done` | Completed — leaves the active list, keeps the row |

## Not the task API

- `/api/ledger?from=YYYY-MM-DD&to=YYYY-MM-DD` — daily discipline marks; a
  separate table, one row per day, `{date, items: {run, strength, rust, trade}, note}`.
- `/api/me`, `/api/account/token`, `/api/auth/*` — session-cookie endpoints. A
  bearer token gets `401` there; that is expected and not a broken token.

## curl, done right

```bash
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
B=https://dev.holdingxs.xyz

curl -s -A "$UA" -H "Authorization: Bearer $HX_TOKEN" $B/api/tasks

curl -s -A "$UA" -H "Authorization: Bearer $HX_TOKEN" -H 'content-type: application/json' \
  -X POST -d '{"title":"ATAS notes","status":"in_progress"}' $B/api/tasks

curl -s -A "$UA" -H "Authorization: Bearer $HX_TOKEN" -H 'content-type: application/json' \
  -X PATCH -d '{"status":"done"}' $B/api/tasks/atas-notes

curl -s -A "$UA" -H "Authorization: Bearer $HX_TOKEN" \
  -X DELETE $B/api/tasks/atas-notes
```
