package main

import (
	"archive/zip"
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/relic/cli/pkg/relic"
)

func TestNoteTextFromArgsAndStdin(t *testing.T) {
	got, err := noteText([]string{"deploy", "went", "fine"}, strings.NewReader("ignored"), true)
	if err != nil || got != "deploy went fine" {
		t.Fatalf("args: %q %v", got, err)
	}
	got, err = noteText(nil, strings.NewReader("  piped text\n"), true)
	if err != nil || got != "piped text" {
		t.Fatalf("stdin: %q %v", got, err)
	}
	if _, err = noteText(nil, strings.NewReader(""), false); err == nil {
		t.Fatal("no args and no pipe should be an error")
	}
}

func TestWithTags(t *testing.T) {
	if got := withTags("built it", []string{"CI", "#infra", " "}); got != "built it #ci #infra" {
		t.Fatalf("got %q", got)
	}
}

func TestChooseJournal(t *testing.T) {
	journals := []relic.JournalInfo{
		{ID: "aaaa1111bbbb2222cccc3333dddd4444", Name: "Work log"},
		{ID: "eeee5555ffff6666aaaa7777bbbb8888", Name: "Personal"},
	}
	if j, err := chooseJournal(journals, ""); err != nil || j.Name != "Work log" {
		t.Fatalf("default: %v %v", j, err)
	}
	if j, err := chooseJournal(journals, "personal"); err != nil || j.Name != "Personal" {
		t.Fatalf("by name: %v %v", j, err)
	}
	if j, err := chooseJournal(journals, "eeee5555"); err != nil || j.Name != "Personal" {
		t.Fatalf("by prefix: %v %v", j, err)
	}
	if _, err := chooseJournal(journals, "nope"); err == nil || !strings.Contains(err.Error(), "Work log") {
		t.Fatalf("unknown should list the choices: %v", err)
	}
	if _, err := chooseJournal(nil, ""); err == nil {
		t.Fatal("no journals should be an error")
	}
}

func TestSafeJoinRefusesEscapes(t *testing.T) {
	dir := t.TempDir()
	if p, err := safeJoin(dir, "2026/09/a.md"); err != nil || p != filepath.Join(dir, "2026", "09", "a.md") {
		t.Fatalf("normal: %q %v", p, err)
	}
	for _, bad := range []string{"../evil.md", "/etc/passwd", "a/../../evil.md"} {
		if _, err := safeJoin(dir, bad); err == nil {
			t.Fatalf("%q should be refused", bad)
		}
	}
}

func TestExtractZip(t *testing.T) {
	var buf bytes.Buffer
	w := zip.NewWriter(&buf)
	f, _ := w.Create("2026/09/nginx-tuning.md")
	f.Write([]byte("body"))
	w.Close()

	dir := t.TempDir()
	n, err := extractZip(buf.Bytes(), dir)
	if err != nil || n != 1 {
		t.Fatalf("extract: %d %v", n, err)
	}
	data, err := os.ReadFile(filepath.Join(dir, "2026", "09", "nginx-tuning.md"))
	if err != nil || string(data) != "body" {
		t.Fatalf("file: %q %v", data, err)
	}

	var evil bytes.Buffer
	ew := zip.NewWriter(&evil)
	ef, _ := ew.Create("../escape.md")
	ef.Write([]byte("x"))
	ew.Close()
	if _, err := extractZip(evil.Bytes(), t.TempDir()); err == nil {
		t.Fatal("a zip that escapes the folder must be refused")
	}
}
