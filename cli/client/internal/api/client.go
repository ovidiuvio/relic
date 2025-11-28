package api

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/relic/cli/internal/config"
	"github.com/relic/cli/internal/utils"
	"github.com/relic/cli/pkg/relic"
)

// Client represents an HTTP client for the Relic API
type Client struct {
	BaseURL    string
	ClientKey  string
	HTTPClient *http.Client
	Verbose    bool
}

// NewClient creates a new API client
func NewClient(cfg *config.Config, verbose bool) *Client {
	return &Client{
		BaseURL:   cfg.Server,
		ClientKey: cfg.ClientKey,
		HTTPClient: &http.Client{
			Timeout: time.Duration(cfg.Timeout) * time.Second,
		},
		Verbose: verbose,
	}
}

// doRequest performs an HTTP request with retry logic
func (c *Client) doRequest(req *http.Request) (*http.Response, error) {
	// Add client key header if available
	if c.ClientKey != "" {
		req.Header.Set("X-Client-Key", c.ClientKey)
	}

	// Verbose logging
	if c.Verbose {
		fmt.Printf("[DEBUG] %s %s\n", req.Method, req.URL.String())
		for key, values := range req.Header {
			for _, value := range values {
				// Don't log sensitive headers in full
				if key == "X-Client-Key" && value != "" {
					fmt.Printf("[DEBUG] %s: %s...\n", key, value[:8])
				} else {
					fmt.Printf("[DEBUG] %s: %s\n", key, value)
				}
			}
		}
	}

	backoff := utils.RetryBackoff()
	var lastErr error

	for attempt := 0; attempt <= utils.MaxRetries; attempt++ {
		if attempt > 0 {
			// Wait before retry
			time.Sleep(backoff[attempt-1])
			if c.Verbose {
				fmt.Printf("[DEBUG] Retry attempt %d/%d\n", attempt, utils.MaxRetries)
			}
		}

		resp, err := c.HTTPClient.Do(req)
		if err != nil {
			lastErr = err
			if utils.ShouldRetry(attempt) {
				continue
			}
			return nil, utils.NewCLIError(fmt.Sprintf("Network error: %v", err), utils.ExitNetworkError)
		}

		// Check if we should retry based on status code
		if utils.IsRetryableError(resp.StatusCode) && utils.ShouldRetry(attempt) {
			lastErr = fmt.Errorf("server returned %d", resp.StatusCode)
			resp.Body.Close()
			continue
		}

		// Verbose response logging
		if c.Verbose {
			fmt.Printf("[DEBUG] Response: %d %s\n", resp.StatusCode, resp.Status)
		}

		return resp, nil
	}

	return nil, utils.NewCLIError(fmt.Sprintf("Max retries exceeded: %v", lastErr), utils.ExitNetworkError)
}

// get performs a GET request
func (c *Client) get(path string) (*http.Response, error) {
	url := c.BaseURL + path
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return nil, err
	}

	return c.doRequest(req)
}

// post performs a POST request
func (c *Client) post(path string, body io.Reader, contentType string) (*http.Response, error) {
	url := c.BaseURL + path
	req, err := http.NewRequest("POST", url, body)
	if err != nil {
		return nil, err
	}

	if contentType != "" {
		req.Header.Set("Content-Type", contentType)
	}

	return c.doRequest(req)
}

// delete performs a DELETE request
func (c *Client) delete(path string) (*http.Response, error) {
	url := c.BaseURL + path
	req, err := http.NewRequest("DELETE", url, nil)
	if err != nil {
		return nil, err
	}

	return c.doRequest(req)
}

// parseErrorResponse parses an error response from the API
func parseErrorResponse(resp *http.Response) error {
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return utils.GetErrorFromStatus(resp.StatusCode, resp.Status)
	}

	var errResp relic.ErrorResponse
	if err := json.Unmarshal(body, &errResp); err != nil {
		return utils.GetErrorFromStatus(resp.StatusCode, string(body))
	}

	return utils.GetErrorFromStatus(resp.StatusCode, errResp.Detail)
}

// RegisterClient registers the client key with the server
func (c *Client) RegisterClient() (*relic.ClientInfo, error) {
	resp, err := c.post("/api/v1/client/register", nil, "")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, parseErrorResponse(resp)
	}

	var info relic.ClientInfo
	if err := json.NewDecoder(resp.Body).Decode(&info); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &info, nil
}

// GetRelic retrieves metadata for a relic
func (c *Client) GetRelic(relicID string) (*relic.RelicMetadata, error) {
	resp, err := c.get(fmt.Sprintf("/api/v1/relics/%s", relicID))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, parseErrorResponse(resp)
	}

	var metadata relic.RelicMetadata
	if err := json.NewDecoder(resp.Body).Decode(&metadata); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &metadata, nil
}

// GetRelicContent downloads the content of a relic
func (c *Client) GetRelicContent(relicID string) (io.ReadCloser, error) {
	resp, err := c.get(fmt.Sprintf("/%s/raw", relicID))
	if err != nil {
		return nil, err
	}

	if resp.StatusCode != http.StatusOK {
		defer resp.Body.Close()
		return nil, parseErrorResponse(resp)
	}

	return resp.Body, nil
}

// ListRelics lists recent public relics
func (c *Client) ListRelics(limit, offset int) (*relic.RelicListResponse, error) {
	path := fmt.Sprintf("/api/v1/relics?limit=%d&offset=%d", limit, offset)
	resp, err := c.get(path)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, parseErrorResponse(resp)
	}

	var list relic.RelicListResponse
	if err := json.NewDecoder(resp.Body).Decode(&list); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &list, nil
}

// ListClientRelics lists relics for the authenticated client
func (c *Client) ListClientRelics(limit, offset int, accessLevel string) (*relic.RelicListResponse, error) {
	path := fmt.Sprintf("/api/v1/client/relics?limit=%d&offset=%d", limit, offset)
	if accessLevel != "" {
		path += fmt.Sprintf("&access_level=%s", accessLevel)
	}

	resp, err := c.get(path)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, parseErrorResponse(resp)
	}

	var list relic.RelicListResponse
	if err := json.NewDecoder(resp.Body).Decode(&list); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &list, nil
}

// ForkRelic forks an existing relic
func (c *Client) ForkRelic(relicID string, req *relic.RelicCreateRequest) (*relic.RelicCreateResponse, error) {
	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to encode request: %w", err)
	}

	resp, err := c.post(fmt.Sprintf("/api/v1/relics/%s/fork", relicID), bytes.NewReader(body), "application/json")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated {
		return nil, parseErrorResponse(resp)
	}

	var createResp relic.RelicCreateResponse
	if err := json.NewDecoder(resp.Body).Decode(&createResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &createResp, nil
}

// DeleteRelic deletes a relic
func (c *Client) DeleteRelic(relicID string) error {
	resp, err := c.delete(fmt.Sprintf("/api/v1/relics/%s", relicID))
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusNoContent {
		return parseErrorResponse(resp)
	}

	return nil
}
