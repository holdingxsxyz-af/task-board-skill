#!/usr/bin/env python3
"""Task board client — stdlib only.

    tb list                          the whole board, one line per task
    tb list --json                   raw JSON
    tb show <id>                     one task
    tb add "Title" [--note "..."] [--status in_progress] [--next 2026-11-05]
    tb set <id> [--title "..."] [--note "..."] [--status done] [--next ...]
                [--add-step "text"] [--tick 0] [--untick 0]
    tb done <id>                     shorthand for set <id> --status done
    tb rm <id>                       delete (final; there is no undo)

Env:
    HX_TOKEN   the account's API token (required)
    HX_BASE    default https://dev.holdingxs.xyz

Exit codes: 0 ok, 1 request/usage error, 401 token rejected.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("HX_BASE", "https://dev.holdingxs.xyz").rstrip("/")
TOKEN = os.environ.get("HX_TOKEN", "").strip()
# Cloudflare drops clients that look like scripts (403 error code: 1010).
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
STATUSES = ("in_progress", "on_hold", "planned", "done")


def die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def call(method, path, body=None):
    if not TOKEN:
        die("HX_TOKEN is not set", 1)
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + TOKEN)
    req.add_header("User-Agent", UA)
    req.add_header("Accept", "application/json")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw.strip() else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            payload = json.loads(raw)
        except Exception:
            payload = raw
        if e.code == 401:
            die("401 — token missing, wrong, or rotated", 401)
        die("%s %s -> %s %s" % (method, path, e.code, payload), 1)
    except urllib.error.URLError as e:
        die("network: %s" % e.reason, 1)


def parse(argv):
    """Tiny flag parser: --key value, --flag."""
    out, i = {}, 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--"):
            k = a[2:]
            if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                out[k] = argv[i + 1]
                i += 2
            else:
                out[k] = True
                i += 1
        else:
            out.setdefault("_", []).append(a)
            i += 1
    return out


def fmt(t):
    mark = "x" if t.get("status") == "done" else "-"
    steps = t.get("steps") or []
    ticked = sum(1 for s in steps if s.get("done"))
    prog = " [%d/%d]" % (ticked, len(steps)) if steps else ""
    return "%s %-28s %-10s %s%s" % (mark, t["id"], t.get("status", ""), t.get("updated", ""), prog)


def main():
    if len(sys.argv) < 2:
        die(__doc__.strip())
    cmd = sys.argv[1]
    a = parse(sys.argv[2:])
    pos = a.get("_", [])

    if cmd == "list":
        _, rows = call("GET", "/api/tasks")
        if a.get("json"):
            print(json.dumps(rows, ensure_ascii=False, indent=2))
            return
        if not rows:
            print("(no tasks)")
            return
        for t in rows:
            print(fmt(t))
            if t.get("note"):
                print("    " + t["note"].splitlines()[0][:100])
        return

    if cmd == "show":
        if not pos:
            die("usage: tb show <id>")
        _, rows = call("GET", "/api/tasks")
        hit = [t for t in rows if t["id"] == pos[0]]
        if not hit:
            die("no task with id %r" % pos[0], 1)
        print(json.dumps(hit[0], ensure_ascii=False, indent=2))
        return

    if cmd == "add":
        if not pos:
            die('usage: tb add "Title" [--note ...]')
        body = {"title": " ".join(pos)}
        for k in ("note", "status", "next"):
            if a.get(k):
                body[k] = a[k]
        if body.get("status") and body["status"] not in STATUSES:
            die("status must be one of " + ", ".join(STATUSES))
        code, t = call("POST", "/api/tasks", body)
        print("%s %s" % ("created" if code == 201 else "ok", t["id"]))
        print(fmt(t))
        return

    if cmd == "set" or cmd == "done":
        if not pos:
            die("usage: tb set <id> [--title ...] [--status ...] [--add-step ...]")
        tid = pos[0]
        body = {}
        if cmd == "done":
            body["status"] = "done"
        for k in ("title", "note", "status", "next"):
            if a.get(k) is not None:
                body[k] = a[k]
        if body.get("status") and body["status"] not in STATUSES:
            die("status must be one of " + ", ".join(STATUSES))

        # steps are replaced as a whole: read, edit, send back
        if a.get("add-step") or a.get("tick") is not None or a.get("untick") is not None:
            _, rows = call("GET", "/api/tasks")
            hit = [t for t in rows if t["id"] == tid]
            if not hit:
                die("no task with id %r" % tid, 1)
            steps = hit[0].get("steps") or []
            if a.get("add-step"):
                steps.append({"done": False, "text": str(a["add-step"])})
            for flag, val in (("tick", True), ("untick", False)):
                if a.get(flag) is not None:
                    try:
                        idx = int(a[flag])
                        steps[idx]["done"] = val
                    except (ValueError, IndexError):
                        die("--%s needs a step index that exists" % flag)
            body["steps"] = steps

        if not body:
            die("nothing to change")
        _, t = call("PATCH", "/api/tasks/" + urllib.parse.quote(tid, safe=""), body)
        print(fmt(t))
        return

    if cmd == "rm":
        if not pos:
            die("usage: tb rm <id>")
        call("DELETE", "/api/tasks/" + urllib.parse.quote(pos[0], safe=""))
        print("deleted " + pos[0])
        return

    die("unknown command %r\n\n%s" % (cmd, __doc__.strip()))


if __name__ == "__main__":
    main()
