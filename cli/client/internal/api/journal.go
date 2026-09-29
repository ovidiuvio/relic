package api

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"os"
	"path/filepath"

	"github.com/relic/cli/pkg/relic"
)

// ListJournals lists the authenticated user's journals, newest activity first
func (c *Client) ListJournals() ([]relic.JournalInfo, error) {
	resp, err := c.get("/api/v1/journals")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, parseErrorResponse(resp)
	}

	var journals []relic.JournalInfo
	if err := json.NewDecoder(resp.Body).Decode(&journals); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}
	return journals, nil
}

// CreateJournal creates a journal (restricted unless accessLevel says otherwise)
func (c *Client) CreateJournal(name, accessLevel string) (*relic.JournalInfo, error) {
	payload := map[string]string{"name": name}
	if accessLevel != "" {
		payload["access_level"] = accessLevel
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("failed to encode request: %w", err)
	}

	resp, err := c.post("/api/v1/journals", bytes.NewReader(body), "application/json")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, parseErrorResponse(resp)
	}

	var made relic.JournalInfo
	if err := json.NewDecoder(resp.Body).Decode(&made); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}
	made.AccessLevel = accessLevel
	return &made, nil
}

// AppendToJournal adds a line to today's Log (creating the day's entry when needed)
func (c *Client) AppendToJournal(journalID string, req *relic.JournalAppendRequest) (*relic.JournalEntry, error) {
	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to encode request: %w", err)
	}

	resp, err := c.post(fmt.Sprintf("/api/v1/journals/%s/append", journalID), bytes.NewReader(body), "application/json")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, parseErrorResponse(resp)
	}

	var entry relic.JournalEntry
	if err := json.NewDecoder(resp.Body).Decode(&entry); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}
	return &entry, nil
}

// OpenDaily opens (creating from the Daily template if missing) the entry for a date
func (c *Client) OpenDaily(journalID, date string) (*relic.JournalEntry, error) {
	body, err := json.Marshal(map[string]string{"entry_date": date})
	if err != nil {
		return nil, fmt.Errorf("failed to encode request: %w", err)
	}

	resp, err := c.post(fmt.Sprintf("/api/v1/journals/%s/daily", journalID), bytes.NewReader(body), "application/json")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, parseErrorResponse(resp)
	}

	var entry relic.JournalEntry
	if err := json.NewDecoder(resp.Body).Decode(&entry); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}
	return &entry, nil
}

// ExportJournal downloads the journal as a zip of Markdown files
func (c *Client) ExportJournal(journalID string) ([]byte, error) {
	resp, err := c.get(fmt.Sprintf("/api/v1/journals/%s/export", journalID))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, parseErrorResponse(resp)
	}
	return io.ReadAll(resp.Body)
}

// ImportJournal uploads Markdown files (or zips of them) into a journal
func (c *Client) ImportJournal(journalID string, paths []string) (*relic.JournalImportResult, error) {
	var buf bytes.Buffer
	writer := multipart.NewWriter(&buf)
	for _, path := range paths {
		file, err := os.Open(path)
		if err != nil {
			return nil, fmt.Errorf("cannot read %s: %w", path, err)
		}
		part, err := writer.CreateFormFile("files", filepath.Base(path))
		if err == nil {
			_, err = io.Copy(part, file)
		}
		file.Close()
		if err != nil {
			return nil, fmt.Errorf("cannot read %s: %w", path, err)
		}
	}
	if err := writer.Close(); err != nil {
		return nil, err
	}

	resp, err := c.post(fmt.Sprintf("/api/v1/journals/%s/import", journalID), &buf, writer.FormDataContentType())
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, parseErrorResponse(resp)
	}

	var result relic.JournalImportResult
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}
	return &result, nil
}
