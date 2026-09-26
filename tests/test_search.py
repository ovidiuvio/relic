"""Integration tests for relic search: words match independently, "quoted phrases" match whole,
and sort_by=relevance puts the best name matches first.

Each test searches a fresh user's own relics (/api/v1/user/relics) with a unique token, so other
data on the deployment can't change the results.
"""
import uuid
import pytest


@pytest.fixture
def searcher(http):
    key = uuid.uuid4().hex
    headers = {"X-User-Key": key}
    http.post("/api/v1/user/register", headers=headers)
    created = []

    def make(name, tags=()):
        data = {"name": name, "access_level": "private"}
        if tags:
            data["tags"] = ",".join(tags)
        resp = http.post("/api/v1/relics", headers=headers, data=data, files={"file": ("f.txt", b"x", "text/plain")})
        assert resp.status_code == 200, resp.text
        created.append(resp.json()["id"])
        return resp.json()["id"]

    def search(q, **params):
        resp = http.get("/api/v1/user/relics", headers=headers, params={"search": q, "limit": 100, **params})
        assert resp.status_code == 200, resp.text
        return resp.json()

    yield make, search
    for relic_id in created:
        http.delete(f"/api/v1/relics/{relic_id}", headers=headers)


def ids(data):
    return {r["id"] for r in data["relics"]}


@pytest.mark.integration
def test_words_match_in_any_order_and_any_field(searcher):
    make, search = searcher
    t = uuid.uuid4().hex[:10]
    both = make(f"{t} queue consumer")
    split = make(f"{t} worker", tags=("queue", "consumer"))
    only_one = make(f"{t} queue only")

    assert ids(search(f"{t} queue consumer")) == {both, split}
    assert ids(search(f"consumer queue {t}")) == {both, split}
    assert ids(search(f"{t}")) == {both, split, only_one}


@pytest.mark.integration
def test_quoted_phrase_matches_whole(searcher):
    make, search = searcher
    t = uuid.uuid4().hex[:10]
    phrase = make(f"{t} queue consumer")
    reversed_ = make(f"{t} consumer queue")
    assert ids(search(f'{t} "queue consumer"')) == {phrase}
    assert ids(search(f"{t} queue consumer")) == {phrase, reversed_}


@pytest.mark.integration
def test_single_word_is_a_substring_match(searcher):
    make, search = searcher
    t = uuid.uuid4().hex[:10]
    rid = make(f"{t}-report")
    assert ids(search(t[2:8])) == {rid}
    assert ids(search(rid[:12])) == {rid}  # ID prefix
    assert search("   ")["total"] >= 1  # a blank search is no filter


@pytest.mark.integration
def test_wildcards_are_literal(searcher):
    make, search = searcher
    t = uuid.uuid4().hex[:10]
    make(f"{t} plain")
    pct = make(f"{t} 100% done")
    assert ids(search(f"{t} %")) == {pct}


@pytest.mark.integration
def test_relevance_puts_name_matches_first(searcher):
    make, search = searcher
    t = uuid.uuid4().hex[:10]
    # Created oldest first, so newest-first order would be the reverse of relevance.
    exact = make(f"{t} alpha")
    prefix = make(f"{t} alpha beta")
    inside = make(f"x {t} alpha")
    words = make(f"alpha x {t}")
    elsewhere = make("unrelated", tags=(t, "alpha"))

    data = search(f"{t} alpha", sort_by="relevance")
    assert [r["id"] for r in data["relics"]] == [exact, prefix, inside, words, elsewhere]
    # Other sorts are untouched by it.
    newest = search(f"{t} alpha")
    assert [r["id"] for r in newest["relics"]] == [elsewhere, words, inside, prefix, exact]
