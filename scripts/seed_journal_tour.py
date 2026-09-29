#!/usr/bin/env python3
"""Create a demo journal, "Journal tour", that shows every feature of Relic journals.

It makes one journal for the user whose key you give, with entries that are themselves the
documentation: a start page, a daily entry with a plan, log lines and tasks, a Markdown cheat
sheet, wiki links and a relic embed, backlinks, kept versions, meetings, weekly reviews, tags,
and a spread of older entries so the timeline and calendar layouts have something to show.
Two small relics (nginx.conf and a diagram) are created for the embeds.

    python scripts/seed_journal_tour.py --server http://localhost --key <your user key>
    python scripts/seed_journal_tour.py --key <key> --replace     # delete an earlier tour first

Needs httpx (pip install httpx). The key defaults to $RELIC_USER_KEY.
"""
import argparse
import os
import sys
from datetime import date, timedelta

import httpx

NAME = "Journal tour"

NGINX_CONF = """server {
    listen 80;
    server_name relic.local;

    # large .rix files were returning 502
    proxy_buffer_size       16k;
    proxy_buffers           8 32k;
    proxy_busy_buffers_size 64k;

    location /api/ {
        proxy_pass http://backend:8000;
        client_max_body_size 100m;
    }
}
"""

DIAGRAM_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 150" width="520" height="150">
  <rect width="520" height="150" fill="#faf8fa"/>
  <g font-family="sans-serif" font-size="14" fill="#211a1f">
    <rect x="20" y="40" width="130" height="70" rx="10" fill="#f5e8f0" stroke="#772953" stroke-width="2"/>
    <text x="85" y="80" text-anchor="middle">Journal (a relic)</text>
    <rect x="195" y="40" width="130" height="70" rx="10" fill="#fff" stroke="#b9b0b8" stroke-width="2"/>
    <text x="260" y="80" text-anchor="middle">2026/09/2026-09-29.md</text>
    <rect x="370" y="40" width="130" height="70" rx="10" fill="#fff" stroke="#b9b0b8" stroke-width="2"/>
    <text x="435" y="80" text-anchor="middle">one file per entry</text>
    <path d="M150 75h45M325 75h45" stroke="#772953" stroke-width="2" fill="none"/>
  </g>
</svg>
"""


def build_entries(today: date, ids: dict):
    """(title, days_ago, body, pinned) for every entry. `ids` holds the demo relics' IDs."""
    d = lambda n: today - timedelta(days=n)  # noqa: E731
    f3 = "```"
    entries = []

    entries.append(("Start here: a tour of Journals", 0, f"""Welcome. Every entry in this journal is a real Markdown file, and each one shows a feature.
This is **Write**: the page looks like this as you type, and the Markdown shows on the line you click. **Source** shows every character, and **Read** is the finished page (top right).

## What to try
- [x] Click a line here to see its Markdown, then try *Source* and *Read*
- [ ] Press <kbd>Ctrl</kbd>+<kbd>J</kbd> anywhere and add a note, then look at today's entry: [[{d(0).strftime('%A')} {d(0).day} {d(0).strftime('%B')}]]
- [ ] Read [[Markdown cheat sheet]], then [[Linking entries and relics]]
- [ ] Switch layouts with the four icons in the bar: Entries, List, Timeline, Calendar
- [ ] Open the *History* section in the inspector and restore an earlier version of this page
- [ ] Open the *Journal* tab in the inspector: visibility, people, import, export

## The rest of the tour
1. [[Markdown cheat sheet]] covers headings, lists, tasks, tables, code and quotes.
2. [[Linking entries and relics]] shows wiki links, backlinks and an embedded relic.
3. [[Shortcuts and quick capture]] lists every key and the command line.
4. [[Tags, search and filters]] shows how to find things again.
5. [[Import and export]] explains moving files in and out.

Older entries (weekly reviews, meetings, notes) fill the timeline and the calendar. #tour #start
""", True))

    entries.append((d(0).strftime("%A ") + str(d(0).day) + d(0).strftime(" %B"), 0, f"""## Plan
- [x] Read the tour
- [ ] Add a note with <kbd>Ctrl</kbd>+<kbd>J</kbd>
- [ ] Try the calendar layout
- [ ] Write about a relic you keep coming back to

## Log
- 08:45 Coffee, then the tour. Daily entries like this one have Plan, Log and Notes sections.
- 09:30 Quick capture adds lines like these under **Log** with the time, from any page or from the CLI: `relic note "text"`.
- 11:10 Fixed the 502s on large files, see [[Nginx tuning]] and the config below. #infra

![[nginx.conf]]

## Notes
Tasks above count as *open* until ticked; the list layouts show them as a badge, and **Open tasks** filters to them.

> A journal is a folder of files. Nothing here is locked in.
""", False))

    entries.append(("Markdown cheat sheet", 1, f"""# Heading 1
## Heading 2
### Heading 3

The **outline** in the inspector is built from headings. Text can be **bold**, *italic*, or `inline code`, and a [link](https://example.com) works too.

## Lists and tasks
- A bullet list
  - with a nested item
- Another item

1. A numbered list
2. Second

- [x] A finished task
- [ ] An open task (counted in the list views)

## A table
| Feature | Where | Key |
| --- | --- | --- |
| New entry | page bar | n |
| Today's entry | page bar | t |
| Blocks | in the editor | / |
| Inspector | right side | ] |

## Code
{f3}python
def greet(name):
    return f"hello {{name}}"
{f3}

## Quote
> Write it down while it is still small.

---

Type <kbd>/</kbd> on an empty line for a menu of blocks (headings, tasks, code, table, divider). #tour #markdown
""", False))

    entries.append(("Linking entries and relics", 2, f"""Links make a journal into a small wiki.

## Wiki links
`[[Entry title]]` links to another entry in this journal: [[Nginx tuning]] or [[Start here: a tour of Journals]].
Use an alias to change the text: [[Nginx tuning|the buffer fix]]. A link to an entry that does not exist yet is dashed: [[An idea for later]].

**Backlinks:** open [[Nginx tuning]] and look at *Links* in the inspector. It lists this entry under "Mentions this".

## Embedding a relic
`![[nginx.conf]]` shows a relic inline, by name (yours or public ones) or by its ID:

![[nginx.conf]]

Images show as images:

![[journal-tour.svg]]

Open the *Links* section here to see both relics, and open the relic itself: its inspector has **In your journals**, which lists this entry (only you see that). #tour #links
""", False))

    entries.append(("Shortcuts and quick capture", 3, """## In the journal
| Key | Does |
| --- | --- |
| n | New entry |
| t | Open today's entry |
| / | Block menu (on an empty line, in the editor) |
| Ctrl+B / Ctrl+I | Bold / italic |
| ] | Show or hide the inspector |
| Arrow keys | Move through entries in the list layouts |
| Enter | Open the selected entry |

## Anywhere
- **Ctrl+J** opens quick capture: a strip above the tab bar that adds a timestamped line to today's Log.
- On a phone, the round **+** button does the same.
- The navbar search has a **Journal** scope: type `in:journal` and words, or `tag:` to filter.

## Command line
```bash
relic note "deploy went fine"
make test 2>&1 | tail -5 | relic note --tag ci
relic journal today
relic journal pull ./journal-files
```
#tour #shortcuts
""", False))

    entries.append(("Tags, search and filters", 4, """Any `#word` in the text is a tag. Tags belong to this journal only; they never show up anywhere else in Relic.

- Click a tag in the list to filter by it, or use the tag facets in the List and Timeline layouts.
- **Pinned** and **Open tasks** facets narrow the list further.
- The navbar search (scope *Journal*) looks in titles, text and tags, and shows a preview of the result.
- Pin an entry from the inspector and it moves to the top of the list, under *Pinned*.

Try these: #tour #search #infra #relic-ui #idea
""", False))

    entries.append(("Import and export", 5, """## Export
The *Journal* tab in the inspector has **Export .zip**: every entry as a Markdown file at its path, with front matter:

```yaml
---
title: "Nginx tuning"
date: 2026-09-27
tags: [infra]
pinned: true
---
```

The command line does the same: `relic journal pull ./folder`.

## Import
Drop Markdown files, folders' worth of them, or a zip (such as an export) on the *Import* box. A file named `2026-09-29.md` becomes that day's entry; a file with front matter keeps its title, date and tags.

## Sharing
A new journal is **restricted**: only you, admins and people you add can read it. The *Journal* tab changes that, and lists the people. Reading is never the same as writing: only the owner edits. #tour #import
""", False))

    entries.append(("Nginx tuning", 6, f"""Settings that fixed the 502s on large `.rix` files:

- `proxy_buffer_size 16k`
- `proxy_buffers 8 32k`
- `proxy_busy_buffers_size 64k`

![[{ids['nginx']}]]

That embed uses the relic's ID instead of its name; both work.

Related: [[Weekly review · week 39]] and the tour's [[Linking entries and relics]]. #infra
""", False))

    entries.append(("Weekly review · week 39", 7, """## Wins
- Pinned spaces landed
- Admin backups are stable

## What slipped
- Docs screenshots

## Next week
- [ ] Journal phase 2
- [ ] Fix the fork lineage edge case #relic-ui
""", False))

    entries.append(("Meeting: infra sync", 9, """**Attendees:** Ovidiu, Dana

## Agenda
- Backup retention
- Rate limits across workers

## Notes
Retention moves to 30 days. In-memory limits are per worker; Redis would share them.

## Actions
- [ ] Move retention to 30 days #infra
- [ ] Check worker-local state in the scheduled jobs
""", False))

    entries.append(("Design round 3: feedback", 12, """Feedback from the third round of UI designs.

- Editor is the base
- No modals, ever
- Search lives in the navbar and reuses the Recent row

Still open: a viewer nobody dislikes. #relic-ui
""", False))

    entries.append(("Rate limit design", 16, """## Options
- In-memory per worker (what we have)
- Redis shared counters
- Postgres advisory locks

Leaning Redis if it is added for anything else. #infra #idea
""", False))

    entries.append(("Book notes: A Philosophy of Software Design", 26, """Deep modules, small interfaces.

> The best modules are those whose interfaces are much simpler than their implementations.

Apply this to the storage wrapper. #idea
""", False))

    entries.append(("Trip planning", 41, """- Train on Saturday morning
- Book the hotel near the old town
- [ ] Check opening hours for the museum
""", False))

    entries.append(("Q3 goals", 68, """## Goals
1. Ship the new UI
2. Admin runtime settings
3. Journal

Review at the end of September. #relic-ui
""", False))

    entries.append(("Retro: first half", 95, """## Went well
- Search relevance
- Backups

## Did not
- Too many parallel branches
""", False))
    return entries


# Older daily entries: (days ago, Log lines)
DAILIES = [
    (1, ["10:02 Restore test on the dev DB took about 40 s.", "15:50 Search token idea: `in:journal`. #relic-ui"]),
    (3, ["11:20 Debugged the flaky admin job tests. Worker-local state again. #infra"]),
    (4, ["09:10 Planning for the week.", "17:30 Shipped the archive preview change. #relic-ui"]),
    (8, ["13:40 Read the search relevance code. Names weigh more than descriptions."]),
    (10, ["09:00 Triaged the reports queue.", "16:20 Two false positives, one real. #infra"]),
    (13, ["10:30 Back from leave. Inbox zero by noon."]),
    (20, ["09:45 Started the design system tokens.", "17:10 Tokens build script works. #relic-ui"]),
    (21, ["12:00 Lunch with Dana, talked about spaces permissions."]),
    (33, ["09:00 Rewrote the README screenshots section."]),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--server", default=os.getenv("RELIC_SERVER", "http://localhost"))
    ap.add_argument("--key", default=os.getenv("RELIC_USER_KEY"), help="the user key that will own the journal")
    ap.add_argument("--replace", action="store_true", help=f'delete an existing journal named "{NAME}" first')
    ap.add_argument("--today", help="pretend today is YYYY-MM-DD (default: today)")
    args = ap.parse_args()
    if not args.key:
        ap.error("give --key (or set RELIC_USER_KEY)")
    today = date.fromisoformat(args.today) if args.today else date.today()

    client = httpx.Client(base_url=args.server, headers={"X-User-Key": args.key, "User-Agent": "curl/7.68.0"}, timeout=30, follow_redirects=True)

    def call(method, path, expect=200, **kw):
        r = client.request(method, path, **kw)
        if r.status_code != expect:
            sys.exit(f"{method} {path} -> {r.status_code}: {r.text[:300]}")
        return r.json() if r.content else None

    existing = [j for j in call("GET", "/api/v1/journals") if j["name"] == NAME]
    if existing and not args.replace:
        sys.exit(f'You already have a journal named "{NAME}" ({existing[0]["id"]}). Use --replace to make a new one.')
    for j in existing:
        call("DELETE", f"/api/v1/relics/{j['id']}")
        print(f"deleted the earlier tour {j['id']}")

    # The relics the embeds point at (private, owned by the same user).
    def make_relic(name, content, mime):
        r = client.post("/api/v1/relics", data={"name": name, "access_level": "private"}, files={"file": (name, content, mime)})
        if r.status_code != 200:
            sys.exit(f"could not create {name}: {r.status_code} {r.text[:200]}")
        return r.json()["id"]

    ids = {
        "nginx": make_relic("nginx.conf", NGINX_CONF.encode(), "text/plain"),
        "diagram": make_relic("journal-tour.svg", DIAGRAM_SVG.encode(), "image/svg+xml"),
    }

    jid = call("POST", "/api/v1/journals", json={"name": NAME})["id"]
    base = f"/api/v1/journals/{jid}"
    made = {}

    for title, ago, body, pinned in build_entries(today, ids):
        day = today - timedelta(days=ago)
        if title == (today.strftime("%A ") + str(today.day) + today.strftime(" %B")):
            # today's entry is the daily one, so quick capture and "Today" find it
            entry = call("POST", f"{base}/daily", json={"entry_date": day.isoformat()})
            entry = call("PATCH", f"{base}/entries/{entry['id']}", json={"body": body})
        else:
            entry = call("POST", f"{base}/entries", json={"title": title, "body": body, "entry_date": day.isoformat(), "pinned": pinned})
        made[title] = entry["id"]

    for ago, lines in DAILIES:
        day = (today - timedelta(days=ago)).isoformat()
        for line in lines:
            time, _, text = line.partition(" ")
            call("POST", f"{base}/append", json={"text": text, "entry_date": day, "time": time})

    # A few kept versions, so History has something to restore.
    for title, edits in (
        ("Start here: a tour of Journals", [" (First draft: only the intro.)"]),
        ("Nginx tuning", ["\n\nEarlier idea: raise `client_max_body_size` instead. That was not it."]),
    ):
        eid = made[title]
        current = call("GET", f"{base}/entries/{eid}")
        call("POST", f"{base}/entries/{eid}/revisions")
        call("PATCH", f"{base}/entries/{eid}", json={"body": current["body"] + edits[0]})
        call("POST", f"{base}/entries/{eid}/revisions")
        call("PATCH", f"{base}/entries/{eid}", json={"body": current["body"]})

    info = call("GET", base)
    print(f'Created "{NAME}" with {info["entry_count"]} entries ({info["size_bytes"]} bytes)')
    print(f"  {args.server}/journal/{jid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
