package main

import (
	"archive/zip"
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/relic/cli/internal/api"
	"github.com/relic/cli/internal/ui"
	"github.com/relic/cli/internal/utils"
	"github.com/relic/cli/pkg/relic"
	"github.com/spf13/cobra"
)

// journalClient returns an API client with a registered user key.
func journalClient() (*api.Client, error) {
	cfg, err := loadConfig()
	if err != nil {
		return nil, err
	}
	key, err := ensureRegisteredUser(cfg)
	if err != nil {
		return nil, err
	}
	client := api.NewClient(cfg, verbose)
	client.UserKey = key
	return client, nil
}

// pickJournal finds the journal a command means: --journal (an ID, an ID prefix or a name),
// else $RELIC_JOURNAL, else the one with the most recent activity.
func pickJournal(client *api.Client, want string) (*relic.JournalInfo, error) {
	if want == "" {
		want = os.Getenv("RELIC_JOURNAL")
	}
	journals, err := client.ListJournals()
	if err != nil {
		return nil, err
	}
	return chooseJournal(journals, want)
}

// chooseJournal picks from a list of journals (newest activity first).
func chooseJournal(journals []relic.JournalInfo, want string) (*relic.JournalInfo, error) {
	if len(journals) == 0 {
		return nil, utils.NewCLIError("You have no journal yet. Create one with: relic journal new \"Work log\"", utils.ExitUsageError)
	}
	if want == "" {
		return &journals[0], nil
	}
	var matches []int
	for i, j := range journals {
		if j.ID == want || strings.EqualFold(j.Name, want) {
			return &journals[i], nil
		}
		if len(want) >= 4 && strings.HasPrefix(j.ID, strings.ToLower(want)) {
			matches = append(matches, i)
		}
	}
	if len(matches) == 1 {
		return &journals[matches[0]], nil
	}
	names := make([]string, 0, len(journals))
	for _, j := range journals {
		names = append(names, fmt.Sprintf("%s (%s)", j.Name, j.ID[:8]))
	}
	return nil, utils.NewCLIError(fmt.Sprintf("No single journal matches %q. Yours: %s", want, strings.Join(names, ", ")), utils.ExitUsageError)
}

// noteText joins the arguments, or reads standard input when there are none and it is piped.
func noteText(args []string, stdin io.Reader, piped bool) (string, error) {
	if len(args) > 0 {
		return strings.TrimSpace(strings.Join(args, " ")), nil
	}
	if !piped {
		return "", utils.NewCLIError("Nothing to add. Give the note as text, or pipe it in.", utils.ExitUsageError)
	}
	data, err := io.ReadAll(stdin)
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(data)), nil
}

// withTags appends #tags to a note (a leading # is accepted).
func withTags(text string, tags []string) string {
	for _, t := range tags {
		t = strings.TrimSpace(strings.TrimPrefix(t, "#"))
		if t != "" {
			text += " #" + strings.ToLower(t)
		}
	}
	return text
}

// noteCmd: relic note "text"  |  something | relic note
func noteCmd() *cobra.Command {
	var journalFlag string
	var noteTags []string
	var each bool

	cmd := &cobra.Command{
		Use:   "note [text]",
		Short: "Add a note to today's journal log",
		Long: `Adds a timestamped line under "Log" in today's journal entry, creating the entry if needed.

  relic note "deploy went fine"
  make test 2>&1 | tail -5 | relic note --tag ci
  git log --oneline -3 | relic note --each     # one note per line`,
		Args: cobra.ArbitraryArgs,
		RunE: func(cmd *cobra.Command, args []string) error {
			text, err := noteText(args, os.Stdin, utils.IsStdin())
			if err != nil {
				return err
			}
			if text == "" {
				return utils.NewCLIError("The note is empty.", utils.ExitUsageError)
			}
			client, err := journalClient()
			if err != nil {
				return err
			}
			journal, err := pickJournal(client, journalFlag)
			if err != nil {
				return err
			}

			notes := []string{text}
			if each {
				notes = notes[:0]
				scanner := bufio.NewScanner(strings.NewReader(text))
				for scanner.Scan() {
					if line := strings.TrimSpace(scanner.Text()); line != "" {
						notes = append(notes, line)
					}
				}
			}
			var entry *relic.JournalEntry
			for _, note := range notes {
				now := time.Now()
				entry, err = client.AppendToJournal(journal.ID, &relic.JournalAppendRequest{
					Text:      withTags(note, noteTags),
					EntryDate: now.Format("2006-01-02"),
					Time:      now.Format("15:04"),
				})
				if err != nil {
					return err
				}
			}

			switch getOutputFormat() {
			case ui.FormatJSON:
				out, _ := json.MarshalIndent(entry, "", "  ")
				fmt.Println(string(out))
			default:
				if !quiet {
					fmt.Fprintf(os.Stderr, "%s %s · %s · %s\n", ui.Success(ui.SymbolSuccess), journal.Name, entry.Path, time.Now().Format("15:04"))
				}
			}
			return nil
		},
	}
	cmd.Flags().StringVarP(&journalFlag, "journal", "j", "", "journal name or ID (default: the one used most recently, or $RELIC_JOURNAL)")
	cmd.Flags().StringArrayVarP(&noteTags, "tag", "t", nil, "add #tags to the note (can be repeated)")
	cmd.Flags().BoolVar(&each, "each", false, "with piped input, add one note per line")
	return cmd
}

// journalCmd: relic journal list|new|today|pull|import
func journalCmd() *cobra.Command {
	var journalFlag string

	cmd := &cobra.Command{
		Use:   "journal",
		Short: "Work with your journals",
	}
	cmd.PersistentFlags().StringVarP(&journalFlag, "journal", "j", "", "journal name or ID (default: the one used most recently, or $RELIC_JOURNAL)")

	cmd.AddCommand(&cobra.Command{
		Use:   "list",
		Short: "List your journals",
		RunE: func(cmd *cobra.Command, args []string) error {
			client, err := journalClient()
			if err != nil {
				return err
			}
			journals, err := client.ListJournals()
			if err != nil {
				return err
			}
			if getOutputFormat() == ui.FormatJSON {
				out, _ := json.MarshalIndent(journals, "", "  ")
				fmt.Println(string(out))
				return nil
			}
			if len(journals) == 0 {
				fmt.Println("No journals yet. Create one with: relic journal new \"Work log\"")
				return nil
			}
			for _, j := range journals {
				fmt.Printf("%-24s %5d entries  %-10s %s\n", j.Name, j.EntryCount, j.AccessLevel, j.ID)
			}
			return nil
		},
	})

	var newAccess string
	newCmd := &cobra.Command{
		Use:   "new NAME",
		Short: "Create a journal (restricted unless you say otherwise)",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			client, err := journalClient()
			if err != nil {
				return err
			}
			made, err := client.CreateJournal(args[0], newAccess)
			if err != nil {
				return err
			}
			if getOutputFormat() == ui.FormatJSON {
				out, _ := json.MarshalIndent(made, "", "  ")
				fmt.Println(string(out))
			} else {
				fmt.Printf("%s Created %q (%s)\n", ui.Success(ui.SymbolSuccess), made.Name, made.ID)
			}
			return nil
		},
	}
	newCmd.Flags().StringVarP(&newAccess, "access-level", "a", "", "public, private (readable by link) or restricted (default)")
	cmd.AddCommand(newCmd)

	cmd.AddCommand(&cobra.Command{
		Use:   "today",
		Short: "Print today's entry (created from the Daily template if missing)",
		RunE: func(cmd *cobra.Command, args []string) error {
			client, err := journalClient()
			if err != nil {
				return err
			}
			journal, err := pickJournal(client, journalFlag)
			if err != nil {
				return err
			}
			entry, err := client.OpenDaily(journal.ID, time.Now().Format("2006-01-02"))
			if err != nil {
				return err
			}
			if getOutputFormat() == ui.FormatJSON {
				out, _ := json.MarshalIndent(entry, "", "  ")
				fmt.Println(string(out))
			} else {
				fmt.Print(entry.Body)
			}
			return nil
		},
	})

	cmd.AddCommand(&cobra.Command{
		Use:   "pull DIR",
		Short: "Download the journal as Markdown files into a folder",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			client, err := journalClient()
			if err != nil {
				return err
			}
			journal, err := pickJournal(client, journalFlag)
			if err != nil {
				return err
			}
			data, err := client.ExportJournal(journal.ID)
			if err != nil {
				return err
			}
			n, err := extractZip(data, args[0])
			if err != nil {
				return err
			}
			if !quiet {
				fmt.Printf("%s %s: %d entries → %s\n", ui.Success(ui.SymbolSuccess), journal.Name, n, args[0])
			}
			return nil
		},
	})

	cmd.AddCommand(&cobra.Command{
		Use:   "import FILE...",
		Short: "Add Markdown files (or zips of them) to a journal",
		Long: `Adds .md files, or .zip files of them (such as a pull), as entries. Front matter (title, date,
tags, pinned) is read; a file named 2026-09-29.md becomes that day's entry and is skipped when the
day already has one.`,
		Args: cobra.MinimumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			client, err := journalClient()
			if err != nil {
				return err
			}
			journal, err := pickJournal(client, journalFlag)
			if err != nil {
				return err
			}
			files, err := expandImportArgs(args)
			if err != nil {
				return err
			}
			result, err := client.ImportJournal(journal.ID, files)
			if err != nil {
				return err
			}
			fmt.Printf("%s %s: %d imported, %d skipped\n", ui.Success(ui.SymbolSuccess), journal.Name, result.Imported, len(result.Skipped))
			for _, s := range result.Skipped {
				fmt.Printf("  skipped %s: %s\n", s.Name, s.Reason)
			}
			return nil
		},
	})

	return cmd
}

// expandImportArgs turns folders into the Markdown files inside them.
func expandImportArgs(args []string) ([]string, error) {
	var files []string
	for _, arg := range args {
		info, err := os.Stat(arg)
		if err != nil {
			return nil, utils.NewCLIError(fmt.Sprintf("Cannot read %s", arg), utils.ExitFileError)
		}
		if !info.IsDir() {
			files = append(files, arg)
			continue
		}
		err = filepath.Walk(arg, func(path string, fi os.FileInfo, walkErr error) error {
			if walkErr != nil {
				return walkErr
			}
			if !fi.IsDir() && isMarkdownName(fi.Name()) {
				files = append(files, path)
			}
			return nil
		})
		if err != nil {
			return nil, err
		}
	}
	if len(files) == 0 {
		return nil, utils.NewCLIError("No Markdown files found.", utils.ExitUsageError)
	}
	return files, nil
}

func isMarkdownName(name string) bool {
	lower := strings.ToLower(name)
	return strings.HasSuffix(lower, ".md") || strings.HasSuffix(lower, ".markdown") || strings.HasSuffix(lower, ".txt") || strings.HasSuffix(lower, ".zip")
}

// safeJoin joins a zip entry's name under dir, refusing names that would land outside it.
func safeJoin(dir, name string) (string, error) {
	clean := filepath.Clean(filepath.FromSlash(name))
	if filepath.IsAbs(clean) || clean == ".." || strings.HasPrefix(clean, ".."+string(filepath.Separator)) {
		return "", fmt.Errorf("unsafe path in archive: %s", name)
	}
	return filepath.Join(dir, clean), nil
}

// extractZip writes a zip's files under dir and returns how many it wrote.
func extractZip(data []byte, dir string) (int, error) {
	reader, err := zip.NewReader(strings.NewReader(string(data)), int64(len(data)))
	if err != nil {
		return 0, fmt.Errorf("the download is not a valid zip: %w", err)
	}
	count := 0
	for _, f := range reader.File {
		if f.FileInfo().IsDir() {
			continue
		}
		target, err := safeJoin(dir, f.Name)
		if err != nil {
			return count, err
		}
		if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
			return count, err
		}
		src, err := f.Open()
		if err != nil {
			return count, err
		}
		dst, err := os.OpenFile(target, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0o644)
		if err != nil {
			src.Close()
			return count, err
		}
		_, copyErr := io.Copy(dst, src)
		src.Close()
		closeErr := dst.Close()
		if copyErr != nil {
			return count, copyErr
		}
		if closeErr != nil {
			return count, closeErr
		}
		count++
	}
	return count, nil
}
