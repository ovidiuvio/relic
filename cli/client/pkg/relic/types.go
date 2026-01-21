package relic

import (
	"encoding/json"
	"time"
)

// RelicTime is a custom time type that handles the backend's ISO format
type RelicTime struct {
	time.Time
}

// UnmarshalJSON parses time in multiple formats
func (rt *RelicTime) UnmarshalJSON(data []byte) error {
	var s string
	if err := json.Unmarshal(data, &s); err != nil {
		return err
	}

	if s == "" || s == "null" {
		return nil
	}

	// Try multiple time formats
	formats := []string{
		time.RFC3339,
		time.RFC3339Nano,
		"2006-01-02T15:04:05.999999", // Python isoformat without timezone
		"2006-01-02T15:04:05",        // Without microseconds
	}

	var parseErr error
	for _, format := range formats {
		t, err := time.Parse(format, s)
		if err == nil {
			rt.Time = t
			return nil
		}
		parseErr = err
	}

	return parseErr
}

// MarshalJSON outputs time in RFC3339 format
func (rt RelicTime) MarshalJSON() ([]byte, error) {
	if rt.Time.IsZero() {
		return []byte("null"), nil
	}
	return json.Marshal(rt.Time.Format(time.RFC3339))
}

// RelicMetadata represents the metadata for a relic
type RelicMetadata struct {
	ID           string     `json:"id"`
	Name         string     `json:"name,omitempty"`
	Description  string     `json:"description,omitempty"`
	ContentType  string     `json:"content_type"`
	LanguageHint string     `json:"language_hint,omitempty"`
	SizeBytes    int64      `json:"size_bytes"`
	AccessLevel  string     `json:"access_level"`
	ForkOf       string     `json:"fork_of,omitempty"`
	CreatedAt    RelicTime  `json:"created_at"`
	ExpiresAt    *RelicTime `json:"expires_at,omitempty"`
	AccessCount  int        `json:"access_count"`
	Tags         []Tag      `json:"tags,omitempty"`
}

// Tag represents a tag associated with a relic
type Tag struct {
	ID   string `json:"id"`
	Name string `json:"name"`
}

// RelicCreateRequest represents the request to create a relic
type RelicCreateRequest struct {
	Name         string   `json:"name,omitempty"`
	Description  string   `json:"description,omitempty"`
	ContentType  string   `json:"content_type"`
	LanguageHint string   `json:"language_hint,omitempty"`
	AccessLevel  string   `json:"access_level"`
	ExpiresIn    string   `json:"expires_in,omitempty"`
	Password     string   `json:"password,omitempty"`
	Tags         []string `json:"tags,omitempty"`
}

// RelicCreateResponse represents the response when creating a relic
type RelicCreateResponse struct {
	ID        string    `json:"id"`
	URL       string    `json:"url"`
	ForkOf    string    `json:"fork_of,omitempty"`
	CreatedAt RelicTime `json:"created_at"`
}

// RelicListResponse represents a list of relics
type RelicListResponse struct {
	Relics []RelicMetadata `json:"relics"`
	Total  int             `json:"total"`
}

// ClientInfo represents information about the client
type ClientInfo struct {
	ClientID   string    `json:"client_id"`
	CreatedAt  RelicTime `json:"created_at"`
	RelicCount int       `json:"relic_count"`
}

// ErrorResponse represents an API error response
type ErrorResponse struct {
	Detail string `json:"detail"`
}
