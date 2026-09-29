"""Unit tests for the pure journal helpers (no server needed)."""
from datetime import date

import pytest

from backend.journal import (
    DAILY_TEMPLATE, JOURNAL_CONTENT_TYPE, append_to_section, count_tasks, daily_title, entry_path,
    count_words, extract_links, extract_tags, format_log_line, parse_front_matter, title_from_filename, is_journal, is_untitled_path, with_front_matter, make_excerpt, parse_body, slugify,
)


@pytest.mark.unit
def test_is_journal():
    assert is_journal(JOURNAL_CONTENT_TYPE)
    assert not is_journal("text/plain")
    assert not is_journal(None)


@pytest.mark.unit
def test_daily_title():
    assert daily_title(date(2026, 9, 29)) == "Tuesday 29 September"
    assert daily_title(date(2026, 1, 1)) == "Thursday 1 January"


@pytest.mark.unit
def test_slugify():
    assert slugify("Nginx tuning") == "nginx-tuning"
    assert slugify("  Weekly review · week 39! ") == "weekly-review-week-39"
    assert slugify("") == "untitled"
    assert slugify("???") == "untitled"
    assert len(slugify("a" * 200)) <= 60


@pytest.mark.unit
def test_entry_path_daily_and_titled():
    day = date(2026, 9, 29)
    assert entry_path(day, "Tuesday 29 September", True, set()) == "2026/09/2026-09-29.md"
    assert entry_path(day, "Nginx tuning", False, set()) == "2026/09/nginx-tuning.md"


@pytest.mark.unit
def test_entry_path_is_unique():
    day = date(2026, 9, 29)
    taken = {"2026/09/nginx-tuning.md", "2026/09/nginx-tuning-2.md"}
    assert entry_path(day, "Nginx tuning", False, taken) == "2026/09/nginx-tuning-3.md"
    assert entry_path(day, "", False, set()) == "2026/09/untitled.md"


@pytest.mark.unit
def test_extract_tags():
    body = "Fixed it. #infra and #Relic-UI\n#infra again\nnot#tag and ## Heading"
    assert extract_tags(body) == ["infra", "relic-ui"]


@pytest.mark.unit
def test_extract_tags_ignores_fenced_code():
    body = "before #real\n```\n#comment in code\n```\nafter"
    assert extract_tags(body) == ["real"]


@pytest.mark.unit
def test_count_tasks():
    body = "- [x] done\n- [ ] open\n* [ ] also open\n1. [x] numbered\n- plain\n```\n- [ ] in code\n```"
    assert count_tasks(body) == {"open": 2, "total": 4}


@pytest.mark.unit
def test_make_excerpt_skips_structure():
    body = "## Plan\n- [x] Ship it\n\n## Log\n- 09:40 Standup\n\n![[nginx.conf]]\n| a | b |\n> quoted"
    assert make_excerpt(body) == "Ship it · 09:40 Standup · quoted"


@pytest.mark.unit
def test_make_excerpt_strips_markup_and_limits_length():
    assert make_excerpt("See [[Nginx tuning]] and `code` and **bold**") == "See Nginx tuning and code and bold"
    assert len(make_excerpt("word " * 200)) <= 160


@pytest.mark.unit
def test_parse_body():
    meta = parse_body("- [ ] one\n- [x] two #infra\ntext")
    assert meta["tags"] == ["infra"]
    assert meta["word_count"] == 4
    assert (meta["open_tasks"], meta["total_tasks"]) == (1, 2)
    assert meta["search_text"].startswith("- [ ] one")


@pytest.mark.unit
def test_format_log_line():
    assert format_log_line("deploy went fine", "14:41") == "- 14:41 deploy went fine"
    assert format_log_line("two\nlines  here") == "- two lines here"


@pytest.mark.unit
def test_append_to_section_adds_after_last_line_of_log():
    body = "## Plan\n- [ ] a\n\n## Log\n- 09:00 one\n- 10:00 two\n\n## Notes\ntext"
    assert append_to_section(body, "- 11:00 three") == (
        "## Plan\n- [ ] a\n\n## Log\n- 09:00 one\n- 10:00 two\n- 11:00 three\n\n## Notes\ntext"
    )


@pytest.mark.unit
def test_append_to_section_replaces_empty_template_bullet():
    result = append_to_section(DAILY_TEMPLATE, "- 09:00 first")
    assert result == "## Plan\n\n## Log\n- 09:00 first\n\n## Notes\n"


@pytest.mark.unit
def test_append_to_section_creates_missing_section():
    assert append_to_section("Some text", "- a") == "Some text\n\n## Log\n- a\n"
    assert append_to_section("", "- a") == "## Log\n- a\n"


@pytest.mark.unit
def test_append_to_section_last_section_and_custom_heading():
    assert append_to_section("## Log\n- a", "- b") == "## Log\n- a\n- b"
    assert append_to_section("## Ideas\n- x\n", "- y", "ideas") == "## Ideas\n- x\n- y\n"


@pytest.mark.unit
def test_append_to_section_ignores_headings_in_code():
    body = "```\n## Log\n```\n\n## Log\n- real"
    assert append_to_section(body, "- new") == "```\n## Log\n```\n\n## Log\n- real\n- new"


@pytest.mark.unit
def test_count_words_ignores_markers():
    assert count_words("") == 0
    assert count_words("- [ ] ask about S3\n- [x] done\n---\n| a | b |\n## Heading here") == 8


@pytest.mark.unit
def test_is_untitled_path():
    assert is_untitled_path("2026/09/untitled.md")
    assert is_untitled_path("2026/09/untitled-3.md")
    assert not is_untitled_path("2026/09/untitled-notes.md")
    assert not is_untitled_path("2026/09/2026-09-29.md")


@pytest.mark.unit
def test_with_front_matter():
    text = with_front_matter('Nginx "tuning"', date(2026, 9, 27), ["infra", "relic-ui"], True, "Body text")
    assert text == '---\ntitle: "Nginx \\"tuning\\""\ndate: 2026-09-27\ntags: [infra, relic-ui]\npinned: true\n---\n\nBody text'
    plain = with_front_matter("", date(2026, 1, 2), [], False, "x")
    assert plain == '---\ntitle: ""\ndate: 2026-01-02\n---\n\nx'


@pytest.mark.unit
def test_is_journal_ignores_case_and_parameters():
    assert is_journal("Application/X-Relic-Journal; charset=utf-8")


@pytest.mark.unit
def test_extract_links():
    body = "## Notes\nSee [[Nginx tuning]] and ![[nginx.conf]] and [[Nginx Tuning|the fix]].\n## Later\n[[Other]]\n```\n[[in code]]\n```"
    links = extract_links(body)
    assert [(l["target"], l["embed"], l["section"]) for l in links] == [
        ("Nginx tuning", False, "Notes"), ("nginx.conf", True, "Notes"), ("Other", False, "Later"),
    ]


@pytest.mark.unit
def test_extract_links_ignores_inline_code():
    links = extract_links("Write `[[Entry title]]` or `![[relic]]` to link, like [[Real one]].")
    assert [l["target"] for l in links] == ["Real one"]


@pytest.mark.unit
def test_parse_front_matter_reads_the_exported_format():
    text = '---\ntitle: "Nginx \\"tuning\\""\ndate: 2026-09-27\ntags: [infra, relic-ui]\npinned: true\nextra: ignored\n---\n\nBody here'
    parsed = parse_front_matter(text)
    assert parsed == {"title": 'Nginx "tuning"', "date": date(2026, 9, 27), "tags": ["infra", "relic-ui"], "pinned": True, "body": "Body here"}


@pytest.mark.unit
def test_parse_front_matter_without_it_is_all_body():
    parsed = parse_front_matter("just text\n---\nmore")
    assert parsed["body"] == "just text\n---\nmore"
    assert parsed["title"] is None and parsed["date"] is None and parsed["tags"] == []
    bad = parse_front_matter("---\ndate: not-a-date\ntags: #a, B\n---\nx")
    assert bad["date"] is None and bad["tags"] == ["a", "b"] and bad["body"] == "x"


@pytest.mark.unit
def test_title_from_filename():
    assert title_from_filename("notes/nginx-tuning.md") == "nginx tuning"
    assert title_from_filename("Weekly_review.MD") == "Weekly review"
    assert title_from_filename("plain.txt") == "plain"


@pytest.mark.unit
def test_make_excerpt_drops_html_tags():
    assert make_excerpt("Press <kbd>Ctrl</kbd>+<kbd>J</kbd> anywhere") == "Press Ctrl+J anywhere"
