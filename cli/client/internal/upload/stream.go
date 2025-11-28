package upload

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"os"
	"path/filepath"

	"github.com/relic/cli/internal/config"
	"github.com/relic/cli/internal/utils"
	"github.com/relic/cli/pkg/relic"
	"github.com/schollz/progressbar/v3"
)

// UploadOptions contains options for uploading a relic
type UploadOptions struct {
	Name         string
	Description  string
	Language     string
	AccessLevel  string
	ExpiresIn    string
	Password     string
	ShowProgress bool
	Verbose      bool
}

// UploadFile uploads a file to the Relic server
func UploadFile(cfg *config.Config, clientKey, filename string, opts *UploadOptions) (*relic.RelicCreateResponse, error) {
	// Check file exists and get size
	fileInfo, err := os.Stat(filename)
	if err != nil {
		return nil, utils.NewCLIError(fmt.Sprintf("File not found: %s", filename), utils.ExitFileError)
	}

	// Check file size
	if fileInfo.Size() > config.MaxFileSize {
		sizeInMB := fileInfo.Size() / (1024 * 1024)
		return nil, utils.NewCLIError(
			fmt.Sprintf("File too large: %dMB (limit: %dMB)", sizeInMB, config.MaxFileSize/(1024*1024)),
			utils.ExitFileError,
		)
	}

	// Open file
	file, err := os.Open(filename)
	if err != nil {
		return nil, utils.NewCLIError(fmt.Sprintf("Failed to open file: %v", err), utils.ExitFileError)
	}
	defer file.Close()

	// Read first 512 bytes for content type detection
	header := make([]byte, 512)
	n, _ := file.Read(header)
	file.Seek(0, 0) // Reset to beginning

	// Detect content type and language
	contentType := DetectContentType(filename, header[:n])
	language := opts.Language
	if language == "" || language == "auto" {
		language = DetectLanguageHint(filename)
	}

	// Set default name if not provided
	name := opts.Name
	if name == "" {
		name = filepath.Base(filename)
	}

	// Upload with progress
	return upload(cfg, clientKey, file, name, contentType, language, fileInfo.Size(), opts)
}

// UploadStdin uploads content from stdin to the Relic server
func UploadStdin(cfg *config.Config, clientKey string, opts *UploadOptions) (*relic.RelicCreateResponse, error) {
	// Read stdin into buffer
	var buf bytes.Buffer
	size, err := io.Copy(&buf, os.Stdin)
	if err != nil {
		return nil, utils.NewCLIError(fmt.Sprintf("Failed to read stdin: %v", err), utils.ExitFileError)
	}

	if size == 0 {
		return nil, utils.NewCLIError("No input provided", utils.ExitUsageError)
	}

	// Check size
	if size > config.MaxFileSize {
		sizeInMB := size / (1024 * 1024)
		return nil, utils.NewCLIError(
			fmt.Sprintf("Input too large: %dMB (limit: %dMB)", sizeInMB, config.MaxFileSize/(1024*1024)),
			utils.ExitFileError,
		)
	}

	// Get buffer content
	content := buf.Bytes()

	// Detect content type
	contentType := DetectContentType("", content[:min(512, int(size))])

	// Set default name if not provided
	name := opts.Name
	if name == "" {
		name = "stdin"
	}

	// Upload - create a new reader from the bytes so we can read from the beginning
	return upload(cfg, clientKey, bytes.NewReader(content), name, contentType, opts.Language, size, opts)
}

// upload performs the actual upload with multipart form data
func upload(cfg *config.Config, clientKey string, reader io.Reader, name, contentType, language string, size int64, opts *UploadOptions) (*relic.RelicCreateResponse, error) {
	// Create multipart form
	var body bytes.Buffer
	writer := multipart.NewWriter(&body)

	// Add metadata fields
	metadata := relic.RelicCreateRequest{
		Name:         name,
		Description:  opts.Description,
		ContentType:  contentType,
		LanguageHint: language,
		AccessLevel:  opts.AccessLevel,
		ExpiresIn:    opts.ExpiresIn,
		Password:     opts.Password,
	}

	if err := writer.WriteField("name", metadata.Name); err != nil {
		return nil, err
	}
	if metadata.Description != "" {
		if err := writer.WriteField("description", metadata.Description); err != nil {
			return nil, err
		}
	}
	if err := writer.WriteField("content_type", metadata.ContentType); err != nil {
		return nil, err
	}
	if metadata.LanguageHint != "" {
		if err := writer.WriteField("language_hint", metadata.LanguageHint); err != nil {
			return nil, err
		}
	}
	if err := writer.WriteField("access_level", metadata.AccessLevel); err != nil {
		return nil, err
	}
	if metadata.ExpiresIn != "" {
		if err := writer.WriteField("expires_in", metadata.ExpiresIn); err != nil {
			return nil, err
		}
	}
	if metadata.Password != "" {
		if err := writer.WriteField("password", metadata.Password); err != nil {
			return nil, err
		}
	}

	// Add file content (backend expects field name "file")
	part, err := writer.CreateFormFile("file", name)
	if err != nil {
		return nil, err
	}

	// Copy content with optional progress bar
	if opts.ShowProgress && utils.IsTTY() && size > 0 {
		bar := progressbar.DefaultBytes(size, "Uploading")
		_, err = io.Copy(io.MultiWriter(part, bar), reader)
		fmt.Println() // New line after progress bar
	} else {
		_, err = io.Copy(part, reader)
	}

	if err != nil {
		return nil, utils.NewCLIError(fmt.Sprintf("Failed to write content: %v", err), utils.ExitFileError)
	}

	writer.Close()

	// Create HTTP request
	url := cfg.Server + "/api/v1/relics"
	req, err := http.NewRequest("POST", url, &body)
	if err != nil {
		return nil, err
	}

	req.Header.Set("Content-Type", writer.FormDataContentType())
	if clientKey != "" {
		req.Header.Set("X-Client-Key", clientKey)
	}

	// Verbose logging
	if opts.Verbose {
		fmt.Printf("[DEBUG] POST %s\n", url)
		fmt.Printf("[DEBUG] Content-Type: %s\n", writer.FormDataContentType())
		if clientKey != "" {
			fmt.Printf("[DEBUG] X-Client-Key: %s...\n", clientKey[:8])
		}
	}

	// Send request
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return nil, utils.NewCLIError(fmt.Sprintf("Network error: %v", err), utils.ExitNetworkError)
	}
	defer resp.Body.Close()

	// Verbose response
	if opts.Verbose {
		fmt.Printf("[DEBUG] Response: %d %s\n", resp.StatusCode, resp.Status)
	}

	// Check response
	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated {
		bodyBytes, _ := io.ReadAll(resp.Body)
		var errResp relic.ErrorResponse
		if err := json.Unmarshal(bodyBytes, &errResp); err == nil {
			return nil, utils.GetErrorFromStatus(resp.StatusCode, errResp.Detail)
		}
		return nil, utils.GetErrorFromStatus(resp.StatusCode, string(bodyBytes))
	}

	// Parse response
	var createResp relic.RelicCreateResponse
	if err := json.NewDecoder(resp.Body).Decode(&createResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &createResp, nil
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
