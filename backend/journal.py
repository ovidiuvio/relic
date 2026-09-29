"""Journal helpers: pure functions for entry bodies, file paths and quick capture.

A journal is a relic (content type JOURNAL_CONTENT_TYPE) whose content is a folder of Markdown
files, one per entry, stored under ``relics/{journal_id}/entries/{path}``. Nothing in this module
touches the database or S3, so it can be tested on its own.
"""
import json
import re
from datetime import date
from typing import Dict, List, Optional, Set

JOURNAL_CONTENT_TYPE = "application/x-relic-journal"

# One entry is one file; keep it far below the relic upload limit.
MAX_BODY_BYTES = 1024 * 1024
# Body text kept in the database so entries can be searched without reading S3.
SEARCH_TEXT_LIMIT = 256 * 1024
EXCERPT_LENGTH = 160
DEFAULT_LOG_HEADING = "Log"

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]

DAILY_TEMPLATE = "## Plan\n\n## Log\n- \n\n## Notes\n"

_TAG_RE = re.compile(r"(?:^|\s)#([a-z][\w-]*)", re.IGNORECASE)
_TASK_RE = re.compile(r"^\s*(?:[-*]|\d+\.)\s+\[( |x)\]\s")
_SKIP_EXCERPT_RE = re.compile(r"^\s*(#{1,3}\s|```|\||---|!\[\[|\d{4}/|\s{2})")
_MARKER_RE = re.compile(r"^\s*(- \[[ x]\]|[-*>]|\d+\.)\s*")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_TASK_MARK_RE = re.compile(r"^\s*(?:[-*]|\d+\.)\s+\[[ x]\]\s", re.MULTILINE)
_WORD_RE = re.compile(r"\S*\w\S*")


def is_journal(content_type: Optional[str]) -> bool:
    """True when a content type marks a relic as a journal (parameters and case are ignored)."""
    return (content_type or "").split(";", 1)[0].strip().lower() == JOURNAL_CONTENT_TYPE


def daily_title(day: date) -> str:
    """Title of a daily entry, e.g. "Tuesday 29 September"."""
    return f"{WEEKDAYS[day.weekday()]} {day.day} {MONTHS[day.month - 1]}"


def slugify(title: str, limit: int = 60) -> str:
    """A file-name-safe slug for a title ("untitled" when nothing usable is left)."""
    slug = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")[:limit].strip("-")
    return slug or "untitled"


def entry_path(day: date, title: str, daily: bool, taken: Set[str]) -> str:
    """Path of a new entry inside the journal, unique among ``taken``.

    Daily entries are named by date (2026/09/2026-09-29.md), others by their title
    (2026/09/nginx-tuning.md); a number is appended when the name is already used.
    """
    stem = day.isoformat() if daily else slugify(title)
    base = f"{day.year:04d}/{day.month:02d}/{stem}"
    path, n = f"{base}.md", 1
    while path in taken:
        n += 1
        path = f"{base}-{n}.md"
    return path


def is_untitled_path(path: str) -> bool:
    """True for the file name an entry gets when created without a title (untitled.md, untitled-2.md)."""
    return re.fullmatch(r"untitled(?:-\d+)?", path.rsplit("/", 1)[-1].removesuffix(".md")) is not None


_LINK_RE = re.compile(r"(!?)\[\[([^\]\n]+)\]\]")


def extract_links(body: str) -> List[Dict]:
    """[[wiki links]] and ![[embeds]] in a body, once per target, with the heading each first sits
    under. A target is the text before an optional "|alias"; fenced code and `inline code` are ignored.
    Returns [{"target", "embed", "section"}], the target as written."""
    links: List[Dict] = []
    seen = set()
    section = ""
    fenced = False
    for line in body.split("\n"):
        if line.startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        heading = _HEADING_RE.match(line)
        if heading:
            section = heading.group(2)
        # `[[in code]]` is text, not a link
        plain = re.sub(r"`[^`\n]+`", lambda m: " " * len(m.group(0)), line)
        for match in _LINK_RE.finditer(plain):
            target = match.group(2).split("|", 1)[0].strip()
            key = target.lower()
            if target and key not in seen:
                seen.add(key)
                links.append({"target": target, "embed": bool(match.group(1)), "section": section})
    return links


def extract_tags(body: str) -> List[str]:
    """#tags in a body, lowercase, in order of first use. Fenced code is ignored."""
    tags: List[str] = []
    fenced = False
    for line in body.split("\n"):
        if line.startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        for match in _TAG_RE.finditer(line):
            tag = match.group(1).lower()
            if tag not in tags:
                tags.append(tag)
    return tags


def count_tasks(body: str) -> Dict[str, int]:
    """Task list items in a body: {"open": n, "total": n}."""
    open_tasks = total = 0
    fenced = False
    for line in body.split("\n"):
        if line.startswith("```"):
            fenced = not fenced
            continue
        match = None if fenced else _TASK_RE.match(line)
        if match:
            total += 1
            if match.group(1) != "x":
                open_tasks += 1
    return {"open": open_tasks, "total": total}


def make_excerpt(body: str, length: int = EXCERPT_LENGTH) -> str:
    """A one-line plain-text summary: the first prose lines, markers and markup removed."""
    parts = []
    fenced = False
    for line in body.split("\n"):
        if line.startswith("```"):
            fenced = not fenced
            continue
        if fenced or not line.strip() or _SKIP_EXCERPT_RE.match(line):
            continue
        text = _MARKER_RE.sub("", line)
        text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
        text = re.sub(r"</?[a-zA-Z][^>]*>", "", text).replace("`", "").replace("*", "")
        if text.strip():
            parts.append(text.strip())
        if sum(len(p) for p in parts) >= length:
            break
    return " · ".join(parts)[:length]


def count_words(body: str) -> int:
    """Words in a body: whitespace-separated tokens that hold a letter or digit, so bullet and
    checkbox markers, rules and table pipes are not counted."""
    return len(_WORD_RE.findall(_TASK_MARK_RE.sub("", body)))


def parse_body(body: str) -> Dict:
    """Everything derived from a body: tags, word count, task counts, excerpt, search text."""
    tasks = count_tasks(body)
    return {
        "tags": extract_tags(body),
        "word_count": count_words(body),
        "open_tasks": tasks["open"],
        "total_tasks": tasks["total"],
        "excerpt": make_excerpt(body),
        "search_text": body[:SEARCH_TEXT_LIMIT],
    }


def format_log_line(text: str, time: Optional[str] = None) -> str:
    """A quick-capture bullet: "- 14:41 text". Line breaks in the text become spaces."""
    flat = " ".join(text.split())
    return f"- {time} {flat}" if time else f"- {flat}"


def append_to_section(body: str, line: str, heading: str = DEFAULT_LOG_HEADING) -> str:
    """Add ``line`` at the end of the ``## heading`` section, creating the section when missing.

    The section ends at the next heading (or the end of the body); the line goes after its last
    non-blank line, so blank lines that separate it from the next section stay in place.
    """
    lines = body.split("\n")
    start: Optional[int] = None
    fenced = False
    for i, current in enumerate(lines):
        if current.startswith("```"):
            fenced = not fenced
            continue
        match = None if fenced else _HEADING_RE.match(current)
        if match and match.group(1) == "##" and match.group(2).lower() == heading.lower():
            start = i
            break
    if start is None:
        base = body.rstrip("\n")
        prefix = f"{base}\n\n" if base else ""
        return f"{prefix}## {heading}\n{line}\n"
    end = len(lines)
    fenced = False
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("```"):
            fenced = not fenced
        if not fenced and _HEADING_RE.match(lines[i]):
            end = i
            break
    last = start
    for i in range(start + 1, end):
        if lines[i].strip():
            last = i
    # A section holding only an empty bullet ("- ") from the template takes the new line in its place
    if last > start and lines[last].strip() in ("-", "- [ ]"):
        lines[last] = line
    else:
        lines.insert(last + 1, line)
    return "\n".join(lines)


def with_front_matter(title: str, day: date, tags: List[str], pinned: bool, body: str) -> str:
    """An entry as an exported Markdown file: YAML front matter (title, date, tags, pinned), then the body."""
    lines = ["---", f"title: {json.dumps(title or '', ensure_ascii=False)}", f"date: {day.isoformat()}"]
    if tags:
        lines.append(f"tags: [{', '.join(tags)}]")
    if pinned:
        lines.append("pinned: true")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body


_FRONT_MATTER_RE = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)", re.DOTALL)


def parse_front_matter(text: str) -> Dict:
    """Split an imported Markdown file into {"title", "date", "tags", "pinned", "body"}.

    Understands the front matter this app exports (title, date, tags as [a, b] or a list, pinned)
    and ignores other keys. Anything unreadable is left out, and a file without front matter is
    all body.
    """
    out: Dict = {"title": None, "date": None, "tags": [], "pinned": False, "body": text}
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        return out
    out["body"] = text[match.end():].lstrip("\n")
    for line in match.group(1).split("\n"):
        key, sep, raw = line.partition(":")
        if not sep:
            continue
        key, raw = key.strip().lower(), raw.strip()
        if key == "title":
            try:
                out["title"] = json.loads(raw) if raw.startswith('"') else raw.strip("'")
            except ValueError:
                out["title"] = raw.strip('"')
        elif key == "date":
            try:
                out["date"] = date.fromisoformat(raw[:10])
            except ValueError:
                pass
        elif key == "tags":
            items = raw.strip("[]").split(",") if raw else []
            out["tags"] = [t.strip().strip('"\'').lstrip("#").lower() for t in items if t.strip()]
        elif key == "pinned":
            out["pinned"] = raw.lower() in ("true", "yes", "1")
    return out


def title_from_filename(name: str) -> str:
    """A title for an imported file with none: its name without folders or extension, dashes as spaces."""
    stem = name.rsplit("/", 1)[-1]
    stem = re.sub(r"\.(?:md|markdown|txt)$", "", stem, flags=re.IGNORECASE)
    return re.sub(r"[-_]+", " ", stem).strip()
