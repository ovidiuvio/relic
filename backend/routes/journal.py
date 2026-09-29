"""Journal endpoints.

A journal is a relic (content type application/x-relic-journal) whose content is a folder of
Markdown files, one per entry, stored at relics/{journal_id}/entries/{path}. Entry metadata lives
in journal_entry so lists and searches never read S3. Journals take no password.

Reading follows the relic rules (private: the URL is the token; restricted: owner, admins and the
access list). Only the owner writes.
"""
import io
import logging
import re
import zipfile
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import asc, desc, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from backend.database import get_db
from backend.dependencies import check_ownership_or_admin, generate_unique_relic_id, get_current_user
from backend.journal import (
    DAILY_TEMPLATE, JOURNAL_CONTENT_TYPE, MAX_BODY_BYTES, SEARCH_TEXT_LIMIT, append_to_section, daily_title,
    entry_path, extract_links, format_log_line, is_journal, is_untitled_path, parse_body, parse_front_matter,
    slugify, title_from_filename, with_front_matter,
)
from backend.models import JournalEntry, JournalEntryLink, JournalEntryRevision, JournalEntryTag, Relic, User
from backend.schemas import (
    JournalAppend, JournalCreate, JournalDaily, JournalEntryCreate, JournalEntryDetail, JournalEntryList,
    JournalEntrySummary, JournalEntryUpdate, JournalResolve, JournalResponse,
)
from backend.storage import storage_service
from backend.utils import clamp_limit, generate_relic_id, is_expired, like_term, search_terms

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/journals")

ENTRY_SORTS = {
    "date": JournalEntry.entry_date,
    "title": func.lower(JournalEntry.title),
    "words": JournalEntry.word_count,
    "tasks": JournalEntry.open_tasks,
    "updated": JournalEntry.updated_at,
}


def entry_key(journal_id: str, path: str) -> str:
    """S3 key of an entry's file."""
    return f"relics/{journal_id}/entries/{path}"


def _today() -> date:
    return datetime.utcnow().date()


def _summary(entry: JournalEntry) -> dict:
    return {
        "id": entry.id, "path": entry.path, "title": entry.title, "entry_date": entry.entry_date,
        "daily": entry.daily, "pinned": entry.pinned, "excerpt": entry.excerpt,
        "word_count": entry.word_count, "open_tasks": entry.open_tasks, "total_tasks": entry.total_tasks,
        "size_bytes": entry.size_bytes, "tags": entry.tag_names,
        "created_at": entry.created_at, "updated_at": entry.updated_at,
    }


def _detail(entry: JournalEntry, body: str, created: bool = False) -> JournalEntryDetail:
    return JournalEntryDetail(**_summary(entry), body=body, created=created)


def _check_body(body: str) -> None:
    if len(body.encode("utf-8")) > MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail=f"An entry can be at most {MAX_BODY_BYTES // 1024} KB")


async def _load_journal(db: AsyncSession, request: Request, journal_id: str, write: bool = False) -> Tuple[Relic, Optional[User]]:
    """The journal relic and the requesting user, after the access checks for reading or writing."""
    result = await db.execute(
        select(Relic).options(selectinload(Relic.access_list), joinedload(Relic.owner)).where(Relic.id == journal_id)
    )
    relic = result.scalar_one_or_none()
    if not relic or not is_journal(relic.content_type):
        raise HTTPException(status_code=404, detail="Journal not found")
    if is_expired(relic.expires_at):
        raise HTTPException(status_code=410, detail="Journal has expired")
    user = await get_current_user(request, db)
    if write:
        if not user:
            raise HTTPException(status_code=401, detail="User key required")
        if relic.user_id != user.id:
            raise HTTPException(status_code=403, detail="Only the owner can change a journal")
    elif relic.access_level == "restricted" and not check_ownership_or_admin(relic, user, require_auth=False):
        if not user or user.id not in {a.user_id for a in relic.access_list}:
            raise HTTPException(status_code=403, detail="Access restricted")
    return relic, user


async def _get_entry(db: AsyncSession, journal_id: str, entry_id: str, lock: bool = False) -> JournalEntry:
    stmt = (
        select(JournalEntry).options(selectinload(JournalEntry.tags), selectinload(JournalEntry.links))
        .where(JournalEntry.id == entry_id, JournalEntry.relic_id == journal_id)
    )
    if lock:
        # Serialises saves of one entry: two quick captures must not overwrite each other's line
        stmt = stmt.with_for_update()
    entry = (await db.execute(stmt)).scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


async def _read_body(entry: JournalEntry) -> str:
    try:
        data = await storage_service.download(entry_key(entry.relic_id, entry.path))
    except Exception as e:
        logger.error(f"Journal entry file missing for {entry.relic_id}/{entry.path}: {e}")
        raise HTTPException(status_code=404, detail="Entry file not found")
    return data.decode("utf-8", errors="replace")


async def _adjust_size(db: AsyncSession, journal_id: str, delta: int) -> None:
    if delta:
        await db.execute(
            update(Relic).where(Relic.id == journal_id)
            .values(size_bytes=func.coalesce(Relic.size_bytes, 0) + delta)
        )


def _apply_meta(entry: JournalEntry, body: str) -> int:
    """Store what is derived from the body on the entry; returns the size change in bytes."""
    meta = parse_body(body)
    size = len(body.encode("utf-8"))
    delta = size - (entry.size_bytes or 0)
    entry.excerpt = meta["excerpt"]
    entry.search_text = meta["search_text"]
    entry.word_count = meta["word_count"]
    entry.open_tasks = meta["open_tasks"]
    entry.total_tasks = meta["total_tasks"]
    entry.size_bytes = size
    wanted = set(meta["tags"])
    current = {t.name: t for t in entry.tags}
    for name, tag in current.items():
        if name not in wanted:
            entry.tags.remove(tag)
    for name in meta["tags"]:
        if name not in current:
            entry.tags.append(JournalEntryTag(entry_id=entry.id, name=name))
    # Links: replace the rows whose targets changed, keep the rest.
    found = {link["target"].lower(): link for link in extract_links(body)}
    have = {link.target: link for link in entry.links}
    for target, link in list(have.items()):
        if target not in found:
            entry.links.remove(link)
    for target, link in found.items():
        row = have.get(target)
        if row is None:
            entry.links.append(JournalEntryLink(entry_id=entry.id, target=target, label=link["target"], embed=link["embed"], section=link["section"]))
        else:
            row.label, row.embed, row.section = link["target"], link["embed"], link["section"]
    return delta


REVISION_PAUSE = timedelta(minutes=10)  # a save after this long a pause keeps the text before it
REVISIONS_KEPT = 30


async def _snapshot(db: AsyncSession, entry: JournalEntry, new_body: Optional[str], force: bool = False) -> Optional[JournalEntryRevision]:
    """Keep the entry's current text as a revision when this save follows a pause (or when asked
    to). Bursts of autosaves share one revision; large entries (whose searchable copy is cut) and
    empty ones are skipped."""
    old = entry.search_text or ""
    if not old.strip() or old == new_body or (entry.size_bytes or 0) > SEARCH_TEXT_LIMIT:
        return None
    if not force and datetime.utcnow() - (entry.updated_at or datetime.utcnow()) < REVISION_PAUSE:
        return None
    revision = JournalEntryRevision(
        id=generate_relic_id(), entry_id=entry.id, title=entry.title, body=old,
        word_count=entry.word_count or 0, created_at=(datetime.utcnow() if force else entry.updated_at) or datetime.utcnow(),
    )
    db.add(revision)
    await db.flush()
    stale = (await db.execute(
        select(JournalEntryRevision.id).where(JournalEntryRevision.entry_id == entry.id)
        .order_by(JournalEntryRevision.created_at.desc()).offset(REVISIONS_KEPT)
    )).scalars().all()
    if stale:
        await db.execute(JournalEntryRevision.__table__.delete().where(JournalEntryRevision.id.in_(stale)))
    return revision


async def _save_body(db: AsyncSession, entry: JournalEntry, body: str, force_revision: bool = False) -> None:
    """Upload a new body for an existing entry and refresh its derived fields."""
    _check_body(body)
    await _snapshot(db, entry, body, force=force_revision)
    delta = _apply_meta(entry, body)
    entry.updated_at = datetime.utcnow()
    await storage_service.upload(entry_key(entry.relic_id, entry.path), body.encode("utf-8"), "text/markdown")
    await _adjust_size(db, entry.relic_id, delta)


async def _create_entry(db: AsyncSession, journal_id: str, *, title: str, body: str, day: date, daily: bool, pinned: bool = False) -> JournalEntry:
    """Insert an entry row, then its file. The row goes first so a path clash is caught before
    S3 is touched (deleting the file after a clash would delete the winner's file)."""
    _check_body(body)
    taken = set((await db.execute(select(JournalEntry.path).where(JournalEntry.relic_id == journal_id))).scalars().all())
    now = datetime.utcnow()
    entry = JournalEntry(
        id=generate_relic_id(), relic_id=journal_id, path=entry_path(day, title, daily, taken), title=title,
        entry_date=day, daily=daily, pinned=pinned, created_at=now, updated_at=now, tags=[], links=[],
    )
    delta = _apply_meta(entry, body)
    db.add(entry)
    await db.flush()  # IntegrityError here means another request took the path
    key = entry_key(journal_id, entry.path)
    await storage_service.upload(key, body.encode("utf-8"), "text/markdown")
    await _adjust_size(db, journal_id, delta)
    try:
        await db.commit()
    except Exception:
        try:
            await storage_service.delete(key)
        except Exception:
            logger.warning(f"Could not clean up journal file {key} after a failed commit")
        raise
    return entry


async def _daily_entry(db: AsyncSession, journal_id: str, day: date, lock: bool = False) -> Optional[JournalEntry]:
    stmt = (
        select(JournalEntry).options(selectinload(JournalEntry.tags), selectinload(JournalEntry.links))
        .where(JournalEntry.relic_id == journal_id, JournalEntry.entry_date == day, JournalEntry.daily.is_(True))
    )
    if lock:
        stmt = stmt.with_for_update()
    return (await db.execute(stmt)).scalars().first()


async def _reload(db: AsyncSession, entry_id: str) -> JournalEntry:
    """Re-read an entry with its tags after a commit."""
    result = await db.execute(
        select(JournalEntry).options(selectinload(JournalEntry.tags))
        .where(JournalEntry.id == entry_id).execution_options(populate_existing=True)
    )
    return result.scalar_one()


def _filtered(journal_id: str, search: Optional[str], after: Optional[date], before: Optional[date],
              pinned: Optional[bool], has_tasks: Optional[bool]):
    """Entries of a journal matching the search, date range, pinned and task filters (not the tag filter)."""
    stmt = select(JournalEntry.id).where(JournalEntry.relic_id == journal_id)
    for term in search_terms(search or ""):
        like = like_term(term)
        tag_ids = select(JournalEntryTag.entry_id).where(JournalEntryTag.name.ilike(like))
        stmt = stmt.where(or_(
            JournalEntry.title.ilike(like), JournalEntry.search_text.ilike(like), JournalEntry.id.in_(tag_ids),
        ))
    if after is not None:
        stmt = stmt.where(JournalEntry.entry_date >= after)
    if before is not None:
        stmt = stmt.where(JournalEntry.entry_date < before)
    if pinned is not None:
        stmt = stmt.where(JournalEntry.pinned.is_(pinned))
    if has_tasks:
        stmt = stmt.where(JournalEntry.open_tasks > 0)
    return stmt


@router.post("", response_model=dict)
async def create_journal(payload: JournalCreate, request: Request, db: AsyncSession = Depends(get_db)):
    """Create a journal. It is a relic owned by the caller, private unless asked otherwise."""
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Valid user key required")
    journal_id = await generate_unique_relic_id(db)
    db.add(Relic(
        id=journal_id, user_id=user.id, name=payload.name, content_type=JOURNAL_CONTENT_TYPE, size_bytes=0,
        s3_key=f"relics/{journal_id}/entries/", access_level=payload.access_level, created_at=datetime.utcnow(),
    ))
    await db.execute(update(User).where(User.id == user.id).values(relic_count=User.relic_count + 1))
    await db.commit()
    return {"id": journal_id, "url": f"/{journal_id}", "name": payload.name}


@router.get("", response_model=List[JournalResponse])
async def list_my_journals(request: Request, db: AsyncSession = Depends(get_db)):
    """The caller's journals, newest activity first."""
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Valid user key required")
    rows = (await db.execute(
        select(Relic, func.count(JournalEntry.id), func.max(JournalEntry.updated_at))
        .outerjoin(JournalEntry, JournalEntry.relic_id == Relic.id)
        .where(Relic.user_id == user.id, Relic.content_type == JOURNAL_CONTENT_TYPE)
        .group_by(Relic.id)
        .order_by(func.coalesce(func.max(JournalEntry.updated_at), Relic.created_at).desc(), Relic.id)
    )).all()
    return [
        JournalResponse(
            id=r.id, name=r.name, access_level=r.access_level, entry_count=count, size_bytes=r.size_bytes or 0,
            created_at=r.created_at, updated_at=updated or r.created_at, expires_at=r.expires_at, can_edit=True,
        )
        for r, count, updated in rows
    ]


@router.get("/mentions/{relic_id}")
async def journal_mentions(relic_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Entries in the caller's own journals that link to or embed a relic, with the heading each
    sits under. Private to the caller: nobody sees what other people wrote about a relic."""
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Valid user key required")
    relic = (await db.execute(select(Relic).where(Relic.id == relic_id))).scalar_one_or_none()
    targets = {relic_id.lower()}
    if relic and relic.name:
        targets.add(relic.name.strip().lower())
    rows = (await db.execute(
        select(JournalEntry, JournalEntryLink, Relic.name)
        .join(JournalEntryLink, JournalEntryLink.entry_id == JournalEntry.id)
        .join(Relic, Relic.id == JournalEntry.relic_id)
        .where(Relic.user_id == user.id, Relic.content_type == JOURNAL_CONTENT_TYPE, JournalEntryLink.target.in_(targets))
        .order_by(JournalEntry.entry_date.desc(), JournalEntry.created_at.desc())
        .limit(50)
    )).all()
    return {"entries": [
        {"journal_id": e.relic_id, "journal_name": name, "id": e.id, "title": e.title, "entry_date": e.entry_date.isoformat(),
         "section": link.section, "embed": link.embed}
        for e, link, name in rows
    ]}


@router.get("/{journal_id}", response_model=JournalResponse)
async def get_journal(journal_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """A journal's details."""
    relic, user = await _load_journal(db, request, journal_id)
    count, updated = (await db.execute(
        select(func.count(JournalEntry.id), func.max(JournalEntry.updated_at)).where(JournalEntry.relic_id == journal_id)
    )).one()
    return JournalResponse(
        id=relic.id, name=relic.name, access_level=relic.access_level, entry_count=count,
        size_bytes=relic.size_bytes or 0, created_at=relic.created_at, updated_at=updated or relic.created_at,
        expires_at=relic.expires_at, can_edit=bool(user and relic.user_id == user.id),
        owner_public_id=relic.owner_public_id, owner_name=relic.owner_name,
    )


@router.get("/{journal_id}/entries", response_model=JournalEntryList)
async def list_entries(
    journal_id: str,
    request: Request,
    search: Optional[str] = None,
    tag: Optional[str] = None,
    after: Optional[date] = None,
    before: Optional[date] = None,
    pinned: Optional[bool] = None,
    has_tasks: Optional[bool] = None,
    sort_by: str = Query("date"),
    sort_order: str = Query("desc"),
    facets: bool = False,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Entries without their bodies. Every search word must match the title, body text or a tag."""
    await _load_journal(db, request, journal_id)
    if sort_by not in ENTRY_SORTS:
        raise HTTPException(status_code=400, detail=f"sort_by must be one of: {', '.join(ENTRY_SORTS)}")
    if sort_order not in ("asc", "desc"):
        raise HTTPException(status_code=400, detail="sort_order must be asc or desc")
    limit = clamp_limit(limit, default=50)
    offset = max(0, offset)

    base = _filtered(journal_id, search, after, before, pinned, has_tasks)
    ids = base
    if tag:
        wanted = tag.strip().lstrip("#").lower()
        ids = base.where(JournalEntry.id.in_(select(JournalEntryTag.entry_id).where(JournalEntryTag.name == wanted)))
    total = (await db.execute(select(func.count()).select_from(ids.subquery()))).scalar() or 0

    direction = asc if sort_order == "asc" else desc
    order = [direction(ENTRY_SORTS[sort_by])]
    if sort_by != "date":
        order.append(desc(JournalEntry.entry_date))
    order += [desc(JournalEntry.created_at), asc(JournalEntry.id)]  # stable offset paging
    stmt = (
        select(JournalEntry).options(selectinload(JournalEntry.tags))
        .where(JournalEntry.id.in_(ids)).order_by(*order).limit(limit).offset(offset)
    )
    entries = (await db.execute(stmt)).scalars().all()

    result = {"entries": [JournalEntrySummary(**_summary(e)) for e in entries], "total": total, "limit": limit, "offset": offset}
    if facets:
        rows = (await db.execute(
            select(JournalEntryTag.name, func.count()).where(JournalEntryTag.entry_id.in_(base))
            .group_by(JournalEntryTag.name).order_by(desc(func.count()), asc(JournalEntryTag.name)).limit(20)
        )).all()
        result["facets"] = {"tags": [{"name": n, "count": c} for n, c in rows]}
    return JournalEntryList(**result)


@router.get("/{journal_id}/days", response_model=List[dict])
async def entry_days(
    journal_id: str, request: Request, after: Optional[date] = None, before: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
    """Entry counts per day (after inclusive, before exclusive), for calendars and week strips."""
    await _load_journal(db, request, journal_id)
    stmt = select(JournalEntry.entry_date, func.count()).where(JournalEntry.relic_id == journal_id)
    if after is not None:
        stmt = stmt.where(JournalEntry.entry_date >= after)
    if before is not None:
        stmt = stmt.where(JournalEntry.entry_date < before)
    rows = (await db.execute(stmt.group_by(JournalEntry.entry_date).order_by(JournalEntry.entry_date))).all()
    return [{"date": d.isoformat(), "count": c} for d, c in rows]


EXPORT_LIMIT_BYTES = 200 * 1024 * 1024


@router.get("/{journal_id}/export")
async def export_journal(journal_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """The whole journal as a .zip: every entry as a Markdown file at its path, with front matter."""
    relic, _ = await _load_journal(db, request, journal_id)
    if (relic.size_bytes or 0) > EXPORT_LIMIT_BYTES:
        raise HTTPException(status_code=413, detail="This journal is too large to export in one go")
    entries = (await db.execute(
        select(JournalEntry).options(selectinload(JournalEntry.tags))
        .where(JournalEntry.relic_id == journal_id).order_by(JournalEntry.path)
    )).scalars().all()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for entry in entries:
            try:
                body = await _read_body(entry)
            except HTTPException:
                body = entry.search_text  # the file is missing from storage: fall back to the searchable copy
            text = with_front_matter(entry.title, entry.entry_date, entry.tag_names, entry.pinned, body)
            archive.writestr(entry.path, text.encode("utf-8"))
    filename = f"{slugify(relic.name or 'journal')}.zip"
    return Response(
        content=buffer.getvalue(), media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


HEX32 = re.compile(r"^[0-9a-f]{32}$")


async def _resolve(db: AsyncSession, journal_id: str, user: Optional[User], targets: List[str]) -> Dict[str, dict]:
    """What [[targets]] point at, keyed by the lowercased target: an entry of this journal (by
    title), a relic (by ID, or by name among the caller's own and public relics), or nothing."""
    wanted = {t.strip().lower(): t.strip() for t in targets if t.strip()}
    out: Dict[str, dict] = {key: {"kind": "missing"} for key in wanted}
    if not wanted:
        return out
    entries = (await db.execute(
        select(JournalEntry).where(JournalEntry.relic_id == journal_id, func.lower(JournalEntry.title).in_(list(wanted)))
        .order_by(JournalEntry.created_at.desc())
    )).scalars().all()
    for e in entries:
        out.setdefault(e.title.lower(), {"kind": "missing"})
        if out[e.title.lower()]["kind"] == "missing":
            out[e.title.lower()] = {"kind": "entry", "id": e.id, "title": e.title, "path": e.path, "entry_date": e.entry_date.isoformat()}
    rest = [k for k, v in out.items() if v["kind"] == "missing"]
    if rest:
        visible = or_(Relic.access_level == "public", Relic.user_id == (user.id if user else None))
        base = select(Relic).where(Relic.content_type != JOURNAL_CONTENT_TYPE, visible)
        ids = [k for k in rest if HEX32.match(k)]
        names = [k for k in rest if k not in ids]
        found: List[Relic] = []
        if ids:
            found += (await db.execute(base.where(Relic.id.in_(ids)))).scalars().all()
        if names:
            found += (await db.execute(base.where(func.lower(Relic.name).in_(names)).order_by(Relic.created_at.desc()))).scalars().all()
        for r in found:
            for key in (r.id, (r.name or "").strip().lower()):
                if key in out and out[key]["kind"] == "missing":
                    out[key] = {"kind": "relic", "id": r.id, "name": r.name, "content_type": r.content_type, "size_bytes": r.size_bytes or 0}
    return out


@router.post("/{journal_id}/resolve")
async def resolve_links(journal_id: str, payload: JournalResolve, request: Request, db: AsyncSession = Depends(get_db)):
    """Resolve the targets of [[links]] and ![[embeds]] for showing an entry: {target: {kind, ...}}."""
    _, user = await _load_journal(db, request, journal_id)
    return await _resolve(db, journal_id, user, payload.targets)


@router.get("/{journal_id}/entries/{entry_id}/backlinks")
async def entry_backlinks(journal_id: str, entry_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """The other entries of this journal that link to this one (by its title), with the heading they sit under."""
    await _load_journal(db, request, journal_id)
    entry = await _get_entry(db, journal_id, entry_id)
    if not entry.title.strip():
        return {"entries": []}
    rows = (await db.execute(
        select(JournalEntry, JournalEntryLink)
        .join(JournalEntryLink, JournalEntryLink.entry_id == JournalEntry.id)
        .where(JournalEntry.relic_id == journal_id, JournalEntry.id != entry_id, JournalEntryLink.target == entry.title.strip().lower())
        .order_by(JournalEntry.entry_date.desc())
    )).all()
    return {"entries": [
        {"id": e.id, "title": e.title, "entry_date": e.entry_date.isoformat(), "path": e.path, "section": link.section}
        for e, link in rows
    ]}


@router.get("/{journal_id}/entries/{entry_id}/revisions")
async def list_revisions(journal_id: str, entry_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Earlier versions of an entry, newest first (owner only)."""
    await _load_journal(db, request, journal_id, write=True)
    await _get_entry(db, journal_id, entry_id)
    rows = (await db.execute(
        select(JournalEntryRevision).where(JournalEntryRevision.entry_id == entry_id)
        .order_by(JournalEntryRevision.created_at.desc())
    )).scalars().all()
    return {"revisions": [{"id": r.id, "title": r.title, "word_count": r.word_count, "created_at": r.created_at} for r in rows]}


@router.get("/{journal_id}/entries/{entry_id}/revisions/{revision_id}")
async def get_revision(journal_id: str, entry_id: str, revision_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """One earlier version of an entry, with its text (owner only). Restoring is a PATCH with this text."""
    await _load_journal(db, request, journal_id, write=True)
    await _get_entry(db, journal_id, entry_id)
    rev = (await db.execute(
        select(JournalEntryRevision).where(JournalEntryRevision.id == revision_id, JournalEntryRevision.entry_id == entry_id)
    )).scalar_one_or_none()
    if not rev:
        raise HTTPException(status_code=404, detail="Revision not found")
    return {"id": rev.id, "title": rev.title, "body": rev.body, "word_count": rev.word_count, "created_at": rev.created_at}


@router.post("/{journal_id}/entries/{entry_id}/revisions")
async def save_version(journal_id: str, entry_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Keep the entry's current text as a named point to come back to (owner only)."""
    await _load_journal(db, request, journal_id, write=True)
    entry = await _get_entry(db, journal_id, entry_id, lock=True)
    revision = await _snapshot(db, entry, None, force=True)
    await db.commit()
    if not revision:
        raise HTTPException(status_code=400, detail="There is nothing to keep yet")
    return {"id": revision.id, "title": revision.title, "word_count": revision.word_count, "created_at": revision.created_at}


@router.post("/{journal_id}/entries/{entry_id}/revisions/{revision_id}/restore", response_model=JournalEntryDetail)
async def restore_revision(journal_id: str, entry_id: str, revision_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Put an earlier version back. The text being replaced is kept as a revision, so this can be undone."""
    await _load_journal(db, request, journal_id, write=True)
    entry = await _get_entry(db, journal_id, entry_id, lock=True)
    rev = (await db.execute(
        select(JournalEntryRevision).where(JournalEntryRevision.id == revision_id, JournalEntryRevision.entry_id == entry_id)
    )).scalar_one_or_none()
    if not rev:
        raise HTTPException(status_code=404, detail="Revision not found")
    entry.title = rev.title
    await _save_body(db, entry, rev.body, force_revision=True)
    await db.commit()
    return _detail(await _reload(db, entry.id), rev.body)


IMPORT_MAX_FILES = 200
_DATED_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _import_sources(name: str, data: bytes) -> List[Tuple[str, bytes]]:
    """The Markdown files inside an upload: the file itself, or the .md/.markdown/.txt files of a zip."""
    lower = name.lower()
    if lower.endswith(".zip"):
        found = []
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for info in archive.infolist():
                n = info.filename
                if info.is_dir() or n.startswith("__MACOSX/") or "/." in f"/{n}" or not n.lower().endswith((".md", ".markdown", ".txt")):
                    continue
                if info.file_size > MAX_BODY_BYTES:
                    found.append((n, b""))  # reported as too large below
                    continue
                found.append((n, archive.read(info)))
        return found
    return [(name, data)]


@router.post("/{journal_id}/import")
async def import_entries(journal_id: str, request: Request, files: List[UploadFile] = File(...), db: AsyncSession = Depends(get_db)):
    """Add Markdown files (or zips of them, such as an export) to the journal as entries. Front
    matter (title, date, tags, pinned) is understood; a file named 2026-09-29.md is that day's daily
    entry, and is skipped when the day already has one. Returns what was added and what was skipped."""
    await _load_journal(db, request, journal_id, write=True)
    sources: List[Tuple[str, bytes]] = []
    skipped: List[dict] = []
    for upload in files:
        data = await upload.read()
        try:
            sources += _import_sources(upload.filename or "entry.md", data)
        except zipfile.BadZipFile:
            skipped.append({"name": upload.filename, "reason": "Not a valid zip file"})
    if len(sources) > IMPORT_MAX_FILES:
        raise HTTPException(status_code=413, detail=f"At most {IMPORT_MAX_FILES} files can be imported at once")
    imported = []
    for name, data in sources:
        if len(data) > MAX_BODY_BYTES or not data:
            skipped.append({"name": name, "reason": "Empty or too large" if not data else "Larger than the entry limit"})
            continue
        parsed = parse_front_matter(data.decode("utf-8", errors="replace"))
        body = parsed["body"].rstrip("\n") + "\n" if parsed["body"].strip() else ""
        missing = [t for t in parsed["tags"] if t not in parse_body(body)["tags"]]
        if missing:  # front matter tags become #tags in the text, where entries keep them
            body = body.rstrip("\n") + ("\n\n" if body else "") + " ".join(f"#{t}" for t in missing) + "\n"
        stem = name.rsplit("/", 1)[-1]
        dated = re.fullmatch(r"(\d{4}-\d{2}-\d{2})\.(?:md|markdown|txt)", stem, re.IGNORECASE)
        found = _DATED_NAME.search(name)
        try:
            day = parsed["date"] or (date.fromisoformat(dated.group(1)) if dated else (date.fromisoformat(found.group(1)) if found else _today()))
        except ValueError:
            day = _today()
        daily = bool(dated)
        if daily and await _daily_entry(db, journal_id, day):
            skipped.append({"name": name, "reason": f"{day.isoformat()} already has a daily entry"})
            continue
        title = (parsed["title"] or (daily_title(day) if daily else title_from_filename(name))).strip()[:200]
        try:
            entry = await _create_entry(db, journal_id, title=title, body=body, day=day, daily=daily, pinned=parsed["pinned"])
        except IntegrityError:
            await db.rollback()
            skipped.append({"name": name, "reason": "Could not be added, try it again"})
            continue
        imported.append({"id": entry.id, "path": entry.path, "title": title})
    return {"imported": len(imported), "entries": imported, "skipped": skipped}


@router.post("/{journal_id}/entries", response_model=JournalEntryDetail)
async def create_journal_entry(journal_id: str, payload: JournalEntryCreate, request: Request, db: AsyncSession = Depends(get_db)):
    """Create an entry."""
    await _load_journal(db, request, journal_id, write=True)
    try:
        entry = await _create_entry(
            db, journal_id, title=(payload.title or "").strip(), body=payload.body,
            day=payload.entry_date or _today(), daily=False, pinned=payload.pinned,
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="An entry with this path already exists, try again")
    return _detail(await _reload(db, entry.id), payload.body)


@router.post("/{journal_id}/daily", response_model=JournalEntryDetail)
async def open_daily_entry(journal_id: str, payload: JournalDaily, request: Request, db: AsyncSession = Depends(get_db)):
    """The daily entry for a date, created from the Daily template when there is none yet."""
    await _load_journal(db, request, journal_id, write=True)
    day = payload.entry_date or _today()
    entry = await _daily_entry(db, journal_id, day)
    if entry:
        return _detail(entry, await _read_body(entry))
    try:
        entry = await _create_entry(db, journal_id, title=daily_title(day), body=DAILY_TEMPLATE, day=day, daily=True)
        created = True
    except IntegrityError:  # a concurrent request created it first
        await db.rollback()
        entry, created = await _daily_entry(db, journal_id, day), False
        if not entry:
            raise HTTPException(status_code=409, detail="Could not create the daily entry, try again")
    entry = await _reload(db, entry.id)
    return _detail(entry, await _read_body(entry), created=created)


@router.post("/{journal_id}/append", response_model=JournalEntryDetail)
async def append_to_daily(journal_id: str, payload: JournalAppend, request: Request, db: AsyncSession = Depends(get_db)):
    """Quick capture: add a line under a heading (Log by default) of a day's entry, creating the entry if needed."""
    await _load_journal(db, request, journal_id, write=True)
    day = payload.entry_date or _today()
    line = format_log_line(payload.text, payload.time)
    for _ in range(2):  # the second pass covers losing the race to create the entry
        entry = await _daily_entry(db, journal_id, day, lock=True)
        if entry:
            body = append_to_section(await _read_body(entry), line, payload.heading)
            await _save_body(db, entry, body)
            await db.commit()
            entry = await _reload(db, entry.id)
            return _detail(entry, body)
        body = append_to_section(DAILY_TEMPLATE, line, payload.heading)
        try:
            entry = await _create_entry(db, journal_id, title=daily_title(day), body=body, day=day, daily=True)
        except IntegrityError:
            await db.rollback()
            continue
        return _detail(await _reload(db, entry.id), body, created=True)
    raise HTTPException(status_code=409, detail="Could not add to the daily entry, try again")


@router.get("/{journal_id}/entries/{entry_id}", response_model=JournalEntryDetail)
async def get_journal_entry(journal_id: str, entry_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """An entry with its Markdown body."""
    await _load_journal(db, request, journal_id)
    entry = await _get_entry(db, journal_id, entry_id)
    return _detail(entry, await _read_body(entry))


@router.patch("/{journal_id}/entries/{entry_id}", response_model=JournalEntryDetail)
async def update_journal_entry(journal_id: str, entry_id: str, payload: JournalEntryUpdate, request: Request, db: AsyncSession = Depends(get_db)):
    """Change an entry's title, body, date or pinned flag.

    A file path is fixed when the entry is created, with one exception: an entry created without a
    title (untitled.md) is renamed after its title the first time it gets one.
    """
    await _load_journal(db, request, journal_id, write=True)
    entry = await _get_entry(db, journal_id, entry_id, lock=True)
    if payload.entry_date is not None and payload.entry_date != entry.entry_date:
        if entry.daily:
            raise HTTPException(status_code=400, detail="A daily entry stays on its date")
        entry.entry_date = payload.entry_date

    old_path = entry.path
    old_body: Optional[str] = None
    if payload.body is None and payload.title is not None:
        old_body = await _read_body(entry)  # read before the path changes
    if payload.title is not None:
        entry.title = payload.title.strip()
        if not entry.daily and is_untitled_path(entry.path) and slugify(entry.title) != "untitled":
            taken = set((await db.execute(
                select(JournalEntry.path).where(JournalEntry.relic_id == journal_id, JournalEntry.id != entry.id)
            )).scalars().all())
            entry.path = entry_path(entry.entry_date, entry.title, False, taken)
    if payload.pinned is not None:
        entry.pinned = payload.pinned

    moved = entry.path != old_path
    try:
        if payload.body is not None:
            body = payload.body
            await _save_body(db, entry, body)  # uploads to the entry's (possibly new) path
        else:
            body = old_body if old_body is not None else await _read_body(entry)
            entry.updated_at = datetime.utcnow()
            if moved:
                await storage_service.upload(entry_key(journal_id, entry.path), body.encode("utf-8"), "text/markdown")
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="An entry with this path already exists, try again")
    if moved:
        try:
            await storage_service.delete(entry_key(journal_id, old_path))
        except Exception as e:
            logger.warning(f"Journal entry {entry_id} moved to {entry.path} but its old file {old_path} remains: {e}")
    return _detail(await _reload(db, entry.id), body)


@router.delete("/{journal_id}/entries/{entry_id}")
async def delete_journal_entry(journal_id: str, entry_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Delete an entry and its file."""
    await _load_journal(db, request, journal_id, write=True)
    entry = await _get_entry(db, journal_id, entry_id, lock=True)
    key = entry_key(journal_id, entry.path)
    size = entry.size_bytes or 0
    await db.delete(entry)
    await _adjust_size(db, journal_id, -size)
    await db.commit()
    try:
        await storage_service.delete(key)
    except Exception as e:
        logger.warning(f"Journal entry {entry_id} removed from the database but its file {key} remains: {e}")
    return {"message": "Entry deleted"}
