"""Integration tests for journals: relics whose content is a folder of Markdown entries."""
import re
import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from tests.conftest import BASE_URL


def hdr(key):
    return {"X-User-Key": key}


@pytest.fixture
def journal(http, registered_user):
    """A private journal (readable by its URL) owned by a fresh user. Deleted afterwards."""
    key, _ = registered_user
    resp = http.post("/api/v1/journals", headers=hdr(key), json={"name": "Work log", "access_level": "private"})
    assert resp.status_code == 200, resp.text
    jid = resp.json()["id"]
    yield {"id": jid, "key": key}
    http.delete(f"/api/v1/relics/{jid}", headers=hdr(key))


def add_entry(http, journal, **payload):
    resp = http.post(f"/api/v1/journals/{journal['id']}/entries", headers=hdr(journal["key"]), json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def entry_url(journal, entry):
    return f"/api/v1/journals/{journal['id']}/entries/{entry['id']}"


class TestJournalLifecycle:
    def test_create_get_and_list(self, http, journal):
        resp = http.get(f"/api/v1/journals/{journal['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Work log"
        assert data["access_level"] == "private"
        assert data["entry_count"] == 0
        assert data["can_edit"] is False  # anonymous read

        mine = http.get("/api/v1/journals", headers=hdr(journal["key"])).json()
        assert [j["id"] for j in mine] == [journal["id"]]
        assert mine[0]["can_edit"] is True

    def test_journal_is_a_relic_of_its_own_type(self, http, journal):
        resp = http.get(f"/api/v1/relics/{journal['id']}")
        assert resp.status_code == 200
        assert resp.json()["content_type"] == "application/x-relic-journal"

    def test_create_requires_a_user_and_a_name(self, http):
        assert http.post("/api/v1/journals", json={"name": "x"}).status_code == 401
        key = uuid.uuid4().hex
        http.post("/api/v1/user/register", headers=hdr(key))
        assert http.post("/api/v1/journals", headers=hdr(key), json={"name": "  "}).status_code == 422

    def test_a_plain_relic_is_not_a_journal(self, http, created_relic):
        assert http.get(f"/api/v1/journals/{created_relic['id']}").status_code == 404
        assert http.get(f"/api/v1/journals/{'0' * 32}").status_code == 404

    def test_raw_and_fork_are_refused(self, http, journal):
        assert http.get(f"/{journal['id']}/raw").status_code == 400
        assert http.post(f"/api/v1/relics/{journal['id']}/fork", headers=hdr(journal["key"])).status_code == 400

    def test_delete_journal_removes_entries(self, http, registered_user):
        key, _ = registered_user
        jid = http.post("/api/v1/journals", headers=hdr(key), json={"name": "Temp"}).json()["id"]
        entry = http.post(f"/api/v1/journals/{jid}/entries", headers=hdr(key), json={"title": "a", "body": "x"}).json()
        assert http.delete(f"/api/v1/relics/{jid}", headers=hdr(key)).status_code == 200
        assert http.get(f"/api/v1/journals/{jid}").status_code == 404
        assert http.get(f"/api/v1/journals/{jid}/entries/{entry['id']}").status_code == 404


class TestDefaultVisibility:
    def test_new_journals_are_restricted_by_default(self, http, registered_user):
        key, _ = registered_user
        jid = http.post("/api/v1/journals", headers=hdr(key), json={"name": "Mine"}).json()["id"]
        try:
            assert http.get(f"/api/v1/journals/{jid}", headers=hdr(key)).json()["access_level"] == "restricted"
            assert http.get(f"/api/v1/relics/{jid}", headers=hdr(key)).json()["access_level"] == "restricted"
            # Knowing the URL is not enough
            assert http.get(f"/api/v1/journals/{jid}").status_code == 403
            assert http.get(f"/api/v1/journals/{jid}/entries").status_code == 403
            stranger = uuid.uuid4().hex
            http.post("/api/v1/user/register", headers=hdr(stranger))
            assert http.get(f"/api/v1/journals/{jid}/entries", headers=hdr(stranger)).status_code == 403
        finally:
            http.delete(f"/api/v1/relics/{jid}", headers=hdr(key))

    def test_people_added_to_the_journal_can_read_but_not_write(self, http, registered_user):
        key, _ = registered_user
        reader = uuid.uuid4().hex
        reader_public_id = http.post("/api/v1/user/register", headers=hdr(reader)).json()["public_id"]
        jid = http.post("/api/v1/journals", headers=hdr(key), json={"name": "Shared"}).json()["id"]
        try:
            entry = http.post(f"/api/v1/journals/{jid}/entries", headers=hdr(key), json={"title": "Hello", "body": "text"}).json()
            added = http.post(f"/api/v1/relics/{jid}/access", headers=hdr(key), json={"public_id": reader_public_id})
            assert added.status_code == 200, added.text
            assert http.get(f"/api/v1/journals/{jid}/entries/{entry['id']}", headers=hdr(reader)).json()["body"] == "text"
            assert http.post(f"/api/v1/journals/{jid}/entries", headers=hdr(reader), json={"body": "x"}).status_code == 403
        finally:
            http.delete(f"/api/v1/relics/{jid}", headers=hdr(key))


class TestEntries:
    def test_create_and_read_back(self, http, journal):
        entry = add_entry(http, journal, title="Nginx tuning", body="Fixed the 502s. #infra\n- [ ] follow up", entry_date="2026-09-27")
        assert entry["path"] == "2026/09/nginx-tuning.md"
        assert entry["tags"] == ["infra"]
        assert (entry["open_tasks"], entry["total_tasks"]) == (1, 1)
        assert entry["daily"] is False

        got = http.get(entry_url(journal, entry)).json()
        assert got["body"] == "Fixed the 502s. #infra\n- [ ] follow up"
        assert got["title"] == "Nginx tuning"
        assert got["excerpt"].startswith("Fixed the 502s.")

    def test_same_title_gets_a_new_path(self, http, journal):
        a = add_entry(http, journal, title="Notes", body="a", entry_date="2026-09-01")
        b = add_entry(http, journal, title="Notes", body="b", entry_date="2026-09-01")
        assert a["path"] == "2026/09/notes.md"
        assert b["path"] == "2026/09/notes-2.md"

    def test_update_body_refreshes_derived_fields_and_size(self, http, journal):
        entry = add_entry(http, journal, title="T", body="one #a #b")
        size_before = http.get(f"/api/v1/journals/{journal['id']}").json()["size_bytes"]
        assert size_before == len("one #a #b")
        resp = http.patch(entry_url(journal, entry), headers=hdr(journal["key"]), json={"body": "one two three #b #c\n- [x] done"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["tags"] == ["b", "c"]
        assert data["word_count"] == 6
        assert (data["open_tasks"], data["total_tasks"]) == (0, 1)
        after = http.get(f"/api/v1/journals/{journal['id']}").json()["size_bytes"]
        assert after == len("one two three #b #c\n- [x] done")
        assert http.get(entry_url(journal, entry)).json()["body"] == "one two three #b #c\n- [x] done"

    def test_update_title_pin_and_date_keep_the_path(self, http, journal):
        entry = add_entry(http, journal, title="Old", body="x", entry_date="2026-09-01")
        data = http.patch(entry_url(journal, entry), headers=hdr(journal["key"]),
                          json={"title": "New", "pinned": True, "entry_date": "2026-09-05"}).json()
        assert (data["title"], data["pinned"], data["entry_date"]) == ("New", True, "2026-09-05")
        assert data["path"] == entry["path"]
        assert data["body"] == "x"

    def test_untitled_entry_is_renamed_once_when_it_gets_a_title(self, http, journal):
        entry = add_entry(http, journal, title="", body="draft text", entry_date="2026-09-29")
        assert entry["path"] == "2026/09/untitled.md"
        named = http.patch(entry_url(journal, entry), headers=hdr(journal["key"]), json={"title": "Nginx tuning"}).json()
        assert named["path"] == "2026/09/nginx-tuning.md"
        assert named["body"] == "draft text"
        assert http.get(entry_url(journal, entry)).json()["body"] == "draft text"
        again = http.patch(entry_url(journal, entry), headers=hdr(journal["key"]), json={"title": "Something else", "body": "new"}).json()
        assert again["path"] == "2026/09/nginx-tuning.md"  # only the first title names the file
        assert http.get(entry_url(journal, entry)).json()["body"] == "new"

    def test_rename_with_a_body_change_and_a_taken_name(self, http, journal):
        add_entry(http, journal, title="Notes", body="a", entry_date="2026-09-01")
        entry = add_entry(http, journal, title="", body="b", entry_date="2026-09-01")
        moved = http.patch(entry_url(journal, entry), headers=hdr(journal["key"]), json={"title": "Notes", "body": "b2"}).json()
        assert moved["path"] == "2026/09/notes-2.md"
        assert http.get(entry_url(journal, entry)).json()["body"] == "b2"
        assert http.get(f"/api/v1/journals/{journal['id']}").json()["size_bytes"] == 3

    def test_delete_entry(self, http, journal):
        entry = add_entry(http, journal, title="Gone", body="12345")
        assert http.delete(entry_url(journal, entry), headers=hdr(journal["key"])).status_code == 200
        assert http.get(entry_url(journal, entry)).status_code == 404
        assert http.get(f"/api/v1/journals/{journal['id']}").json()["size_bytes"] == 0

    def test_body_size_limit(self, http, journal):
        resp = http.post(f"/api/v1/journals/{journal['id']}/entries", headers=hdr(journal["key"]),
                         json={"title": "big", "body": "x" * (1024 * 1024 + 1)})
        assert resp.status_code == 413


class TestListing:
    @pytest.fixture
    def filled(self, http, journal):
        add_entry(http, journal, title="Nginx tuning", body="proxy buffers fixed the 502s on large files #infra", entry_date="2026-09-27")
        add_entry(http, journal, title="Design round", body="editor is the base #relic-ui\n- [ ] viewer", entry_date="2026-09-25", pinned=True)
        add_entry(http, journal, title="Backup review", body="nightly dump #infra\n- [x] done", entry_date="2026-08-15")
        return journal

    def titles(self, http, journal, **params):
        resp = http.get(f"/api/v1/journals/{journal['id']}/entries", params=params)
        assert resp.status_code == 200, resp.text
        return [e["title"] for e in resp.json()["entries"]]

    def test_default_order_is_newest_date_first(self, http, filled):
        assert self.titles(http, filled) == ["Nginx tuning", "Design round", "Backup review"]

    def test_search_matches_title_body_and_tags(self, http, filled):
        assert self.titles(http, filled, search="buffers") == ["Nginx tuning"]
        assert self.titles(http, filled, search="DESIGN") == ["Design round"]
        assert self.titles(http, filled, search="relic-ui") == ["Design round"]
        assert self.titles(http, filled, search="dump infra") == ["Backup review"]
        assert self.titles(http, filled, search="nothing-here") == []

    def test_tag_filter_and_facets(self, http, filled):
        assert self.titles(http, filled, tag="infra") == ["Nginx tuning", "Backup review"]
        assert self.titles(http, filled, tag="#INFRA") == ["Nginx tuning", "Backup review"]
        data = http.get(f"/api/v1/journals/{filled['id']}/entries", params={"facets": "true", "tag": "relic-ui"}).json()
        assert data["total"] == 1
        assert {t["name"]: t["count"] for t in data["facets"]["tags"]} == {"infra": 2, "relic-ui": 1}

    def test_date_range_pinned_and_tasks(self, http, filled):
        assert self.titles(http, filled, after="2026-09-01") == ["Nginx tuning", "Design round"]
        assert self.titles(http, filled, before="2026-09-26") == ["Design round", "Backup review"]
        assert self.titles(http, filled, pinned="true") == ["Design round"]
        assert self.titles(http, filled, has_tasks="true") == ["Design round"]

    def test_sorting_and_paging(self, http, filled):
        assert self.titles(http, filled, sort_by="title", sort_order="asc") == ["Backup review", "Design round", "Nginx tuning"]
        assert self.titles(http, filled, sort_by="words", sort_order="desc")[0] == "Nginx tuning"
        page = http.get(f"/api/v1/journals/{filled['id']}/entries", params={"limit": 2, "offset": 2}).json()
        assert page["total"] == 3 and [e["title"] for e in page["entries"]] == ["Backup review"]
        assert http.get(f"/api/v1/journals/{filled['id']}/entries", params={"sort_by": "nope"}).status_code == 400

    def test_days(self, http, filled):
        days = http.get(f"/api/v1/journals/{filled['id']}/days", params={"after": "2026-09-01"}).json()
        assert days == [{"date": "2026-09-25", "count": 1}, {"date": "2026-09-27", "count": 1}]


class TestDailyAndCapture:
    def test_daily_is_get_or_create(self, http, journal):
        url = f"/api/v1/journals/{journal['id']}/daily"
        first = http.post(url, headers=hdr(journal["key"]), json={"entry_date": "2026-09-29"}).json()
        assert first["created"] is True and first["daily"] is True
        assert first["title"] == "Tuesday 29 September"
        assert first["path"] == "2026/09/2026-09-29.md"
        assert "## Log" in first["body"]
        second = http.post(url, headers=hdr(journal["key"]), json={"entry_date": "2026-09-29"}).json()
        assert second["created"] is False and second["id"] == first["id"]

    def test_daily_entry_stays_on_its_date(self, http, journal):
        daily = http.post(f"/api/v1/journals/{journal['id']}/daily", headers=hdr(journal["key"]), json={"entry_date": "2026-09-29"}).json()
        resp = http.patch(entry_url(journal, daily), headers=hdr(journal["key"]), json={"entry_date": "2026-09-30"})
        assert resp.status_code == 400

    def test_append_creates_then_extends_the_log(self, http, journal):
        url = f"/api/v1/journals/{journal['id']}/append"
        first = http.post(url, headers=hdr(journal["key"]), json={"text": "first thought", "time": "09:00", "entry_date": "2026-09-29"}).json()
        assert first["created"] is True
        assert "## Log\n- 09:00 first thought\n" in first["body"]
        second = http.post(url, headers=hdr(journal["key"]), json={"text": "second\nthought", "time": "10:15", "entry_date": "2026-09-29"}).json()
        assert second["created"] is False and second["id"] == first["id"]
        assert "- 09:00 first thought\n- 10:15 second thought" in second["body"]
        assert http.get(entry_url(journal, first)).json()["body"] == second["body"]

    def test_concurrent_appends_keep_every_line(self, http, journal):
        url = f"{BASE_URL}/api/v1/journals/{journal['id']}/append"

        def send(i):
            with httpx.Client(timeout=30, headers={**hdr(journal["key"]), "User-Agent": "curl/7.68.0"}) as c:
                return c.post(url, json={"text": f"line {i}", "entry_date": "2026-09-29"}).status_code

        with ThreadPoolExecutor(max_workers=6) as pool:
            statuses = list(pool.map(send, range(6)))
        assert statuses == [200] * 6
        entries = http.get(f"/api/v1/journals/{journal['id']}/entries").json()["entries"]
        assert len(entries) == 1
        body = http.get(f"/api/v1/journals/{journal['id']}/entries/{entries[0]['id']}").json()["body"]
        assert sorted(re.findall(r"- (line \d)", body)) == [f"line {i}" for i in range(6)]

    def test_append_needs_text(self, http, journal):
        assert http.post(f"/api/v1/journals/{journal['id']}/append", headers=hdr(journal["key"]), json={"text": ""}).status_code == 422


class TestAccess:
    def test_only_the_owner_writes(self, http, journal):
        entry = add_entry(http, journal, title="Mine", body="secret")
        stranger = uuid.uuid4().hex
        http.post("/api/v1/user/register", headers=hdr(stranger))
        base = f"/api/v1/journals/{journal['id']}"
        assert http.post(f"{base}/entries", json={"body": "x"}).status_code == 401
        assert http.post(f"{base}/entries", headers=hdr(stranger), json={"body": "x"}).status_code == 403
        assert http.patch(entry_url(journal, entry), headers=hdr(stranger), json={"body": "x"}).status_code == 403
        assert http.delete(entry_url(journal, entry), headers=hdr(stranger)).status_code == 403
        assert http.post(f"{base}/append", headers=hdr(stranger), json={"text": "x"}).status_code == 403
        assert http.post(f"{base}/daily", headers=hdr(stranger), json={}).status_code == 403
        assert http.get(entry_url(journal, entry)).json()["body"] == "secret"  # unchanged

    def test_private_journal_is_readable_by_its_url(self, http, journal):
        entry = add_entry(http, journal, title="Shared by link", body="hello")
        assert http.get(entry_url(journal, entry)).status_code == 200
        assert http.get(f"/api/v1/journals/{journal['id']}/entries").status_code == 200

    def test_restricted_journal_hides_from_strangers(self, http, registered_user):
        key, _ = registered_user
        jid = http.post("/api/v1/journals", headers=hdr(key), json={"name": "R", "access_level": "restricted"}).json()["id"]
        try:
            stranger = uuid.uuid4().hex
            http.post("/api/v1/user/register", headers=hdr(stranger))
            assert http.get(f"/api/v1/journals/{jid}").status_code == 403
            assert http.get(f"/api/v1/journals/{jid}/entries", headers=hdr(stranger)).status_code == 403
            assert http.get(f"/api/v1/journals/{jid}/entries", headers=hdr(key)).status_code == 200
        finally:
            http.delete(f"/api/v1/relics/{jid}", headers=hdr(key))


class TestJournalTypeIsProtected:
    def test_a_journal_cannot_be_uploaded_as_a_relic(self, http, registered_user):
        key, _ = registered_user
        resp = http.post(
            "/api/v1/relics", headers=hdr(key), data={"name": "fake", "access_level": "private"},
            files={"file": ("fake.txt", b"x", "application/x-relic-journal")},
        )
        assert resp.status_code == 400
        resp = http.put(
            "/api/v1/relics/raw", headers=hdr(key), params={"content_type": "application/x-relic-journal; charset=utf-8"},
            content=b"x",
        )
        assert resp.status_code == 400

    def test_types_cannot_be_swapped_with_an_update(self, http, journal, created_relic):
        # a journal keeps its type
        resp = http.put(f"/api/v1/relics/{journal['id']}", headers=hdr(journal["key"]), json={"content_type": "text/plain"})
        assert resp.status_code == 400
        # an ordinary relic cannot become a journal
        resp = http.put(
            f"/api/v1/relics/{created_relic['id']}", headers=hdr(created_relic["user_key"]),
            json={"content_type": "application/x-relic-journal"},
        )
        assert resp.status_code == 400
        assert http.get(f"/api/v1/relics/{journal['id']}").json()["content_type"] == "application/x-relic-journal"


class TestExport:
    def test_export_is_a_zip_of_markdown_files_with_front_matter(self, http, journal):
        import io
        import zipfile
        add_entry(http, journal, title="Nginx tuning", body="Fixed 502s #infra", entry_date="2026-09-27", pinned=True)
        add_entry(http, journal, title="Notes", body="plain", entry_date="2026-08-01")
        resp = http.get(f"/api/v1/journals/{journal['id']}/export")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        assert 'filename="work-log.zip"' in resp.headers["content-disposition"]
        archive = zipfile.ZipFile(io.BytesIO(resp.content))
        assert sorted(archive.namelist()) == ["2026/08/notes.md", "2026/09/nginx-tuning.md"]
        text = archive.read("2026/09/nginx-tuning.md").decode()
        assert text == '---\ntitle: "Nginx tuning"\ndate: 2026-09-27\ntags: [infra]\npinned: true\n---\n\nFixed 502s #infra'

    def test_export_follows_read_access(self, http, registered_user):
        key, _ = registered_user
        jid = http.post("/api/v1/journals", headers=hdr(key), json={"name": "R"}).json()["id"]
        try:
            assert http.get(f"/api/v1/journals/{jid}/export").status_code == 403
            assert http.get(f"/api/v1/journals/{jid}/export", headers=hdr(key)).status_code == 200
        finally:
            http.delete(f"/api/v1/relics/{jid}", headers=hdr(key))


class TestLinks:
    def test_resolve_entries_relics_and_missing(self, http, journal, created_relic):
        add_entry(http, journal, title="Nginx tuning", body="x", entry_date="2026-09-27")
        # created_relic is owned by another user and public: resolvable by ID for anyone
        rid = created_relic["id"]
        resp = http.post(f"/api/v1/journals/{journal['id']}/resolve", json={"targets": ["nginx TUNING", rid, "no such thing"]})
        assert resp.status_code == 200
        data = resp.json()
        assert data["nginx tuning"]["kind"] == "entry" and data["nginx tuning"]["path"] == "2026/09/nginx-tuning.md"
        assert data[rid]["kind"] == "relic" and data[rid]["name"] == "Test Relic"
        assert data["no such thing"] == {"kind": "missing"}

    def test_backlinks_and_section_context(self, http, journal):
        target = add_entry(http, journal, title="Nginx tuning", body="the fix", entry_date="2026-09-27")
        add_entry(http, journal, title="Monday", body="## Log\n- 10:00 read [[nginx tuning]]\n## Notes\nnothing", entry_date="2026-09-28")
        add_entry(http, journal, title="Unrelated", body="no links", entry_date="2026-09-29")
        links = http.get(f"{entry_url(journal, target)}/backlinks").json()["entries"]
        assert [(l["title"], l["section"]) for l in links] == [("Monday", "Log")]
        # editing the linking entry updates the backlinks
        monday = http.get(f"/api/v1/journals/{journal['id']}/entries", params={"search": "Monday"}).json()["entries"][0]
        http.patch(f"/api/v1/journals/{journal['id']}/entries/{monday['id']}", headers=hdr(journal["key"]), json={"body": "no link now"})
        assert http.get(f"{entry_url(journal, target)}/backlinks").json()["entries"] == []

    def test_mentions_of_a_relic_are_private_to_its_reader(self, http, journal, created_relic):
        rid = created_relic["id"]
        add_entry(http, journal, title="About it", body=f"## Ideas\nembed ![[{rid}]]", entry_date="2026-09-28")
        mine = http.get(f"/api/v1/journals/mentions/{rid}", headers=hdr(journal["key"])).json()["entries"]
        assert [(m["title"], m["section"], m["embed"]) for m in mine] == [("About it", "Ideas", True)]
        stranger = uuid.uuid4().hex
        http.post("/api/v1/user/register", headers=hdr(stranger))
        assert http.get(f"/api/v1/journals/mentions/{rid}", headers=hdr(stranger)).json()["entries"] == []
        assert http.get(f"/api/v1/journals/mentions/{rid}").status_code == 401


class TestRevisions:
    def test_keep_a_version_and_restore_it(self, http, journal):
        entry = add_entry(http, journal, title="Draft", body="first version", entry_date="2026-09-29")
        base = entry_url(journal, entry)
        kept = http.post(f"{base}/revisions", headers=hdr(journal["key"]))
        assert kept.status_code == 200
        http.patch(base, headers=hdr(journal["key"]), json={"body": "second version"})
        revisions = http.get(f"{base}/revisions", headers=hdr(journal["key"])).json()["revisions"]
        assert len(revisions) == 1
        one = http.get(f"{base}/revisions/{revisions[0]['id']}", headers=hdr(journal["key"])).json()
        assert one["body"] == "first version"
        restored = http.post(f"{base}/revisions/{revisions[0]['id']}/restore", headers=hdr(journal["key"])).json()
        assert restored["body"] == "first version"
        assert http.get(base).json()["body"] == "first version"
        # the replaced text is itself kept
        bodies = [http.get(f"{base}/revisions/{r['id']}", headers=hdr(journal["key"])).json()["body"]
                  for r in http.get(f"{base}/revisions", headers=hdr(journal["key"])).json()["revisions"]]
        assert "second version" in bodies

    def test_nothing_to_keep_for_an_empty_entry_and_owner_only(self, http, journal):
        entry = add_entry(http, journal, title="Empty", body="", entry_date="2026-09-29")
        base = entry_url(journal, entry)
        assert http.post(f"{base}/revisions", headers=hdr(journal["key"])).status_code == 400
        assert http.get(f"{base}/revisions").status_code == 401


class TestImport:
    def test_import_markdown_files_and_an_export_roundtrip(self, http, journal):
        import io
        import zipfile
        files = [
            ("files", ("2026-09-20.md", b"## Log\n- 08:00 imported daily", "text/markdown")),
            ("files", ("nginx-notes.md", b'---\ntitle: "Nginx notes"\ndate: 2026-09-01\ntags: [infra]\npinned: true\n---\n\nBuffers.', "text/markdown")),
            ("files", ("plain.txt", b"just text", "text/plain")),
        ]
        resp = http.post(f"/api/v1/journals/{journal['id']}/import", headers=hdr(journal["key"]), files=files)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["imported"] == 3 and data["skipped"] == []
        entries = {e["title"]: e for e in http.get(f"/api/v1/journals/{journal['id']}/entries").json()["entries"]}
        assert entries["Nginx notes"]["pinned"] is True and entries["Nginx notes"]["tags"] == ["infra"]
        assert entries["Nginx notes"]["entry_date"] == "2026-09-01"
        assert entries["Sunday 20 September"]["daily"] is True and entries["Sunday 20 September"]["path"] == "2026/09/2026-09-20.md"
        assert entries["plain"]["entry_date"]  # no date anywhere: today
        # importing the same daily file again is skipped, not duplicated
        again = http.post(f"/api/v1/journals/{journal['id']}/import", headers=hdr(journal["key"]),
                          files=[("files", ("2026-09-20.md", b"again", "text/markdown"))]).json()
        assert again["imported"] == 0 and "already has a daily entry" in again["skipped"][0]["reason"]
        # an export imports into another journal with everything intact
        archive = http.get(f"/api/v1/journals/{journal['id']}/export").content
        other = http.post("/api/v1/journals", headers=hdr(journal["key"]), json={"name": "Copy"}).json()["id"]
        try:
            copied = http.post(f"/api/v1/journals/{other}/import", headers=hdr(journal["key"]), files=[("files", ("export.zip", archive, "application/zip"))]).json()
            assert copied["imported"] == 3
            titles = sorted(e["title"] for e in http.get(f"/api/v1/journals/{other}/entries", headers=hdr(journal["key"])).json()["entries"])
            assert titles == ["Nginx notes", "Sunday 20 September", "plain"]
        finally:
            http.delete(f"/api/v1/relics/{other}", headers=hdr(journal["key"]))

    def test_import_is_owner_only_and_rejects_bad_zips(self, http, journal):
        other = uuid.uuid4().hex
        http.post("/api/v1/user/register", headers=hdr(other))
        url = f"/api/v1/journals/{journal['id']}/import"
        assert http.post(url, headers=hdr(other), files=[("files", ("a.md", b"x", "text/markdown"))]).status_code == 403
        bad = http.post(url, headers=hdr(journal["key"]), files=[("files", ("broken.zip", b"not a zip", "application/zip"))]).json()
        assert bad["imported"] == 0 and bad["skipped"][0]["reason"] == "Not a valid zip file"
