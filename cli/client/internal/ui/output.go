package ui

import (
	"encoding/json"
	"fmt"
	"os"
	"time"

	"github.com/relic/cli/pkg/relic"
)

// OutputFormat represents the output format type
type OutputFormat string

const (
	FormatHuman OutputFormat = "human"
	FormatJSON  OutputFormat = "json"
	FormatURL   OutputFormat = "url"
)

// PrintRelicCreated prints the result of creating a relic
func PrintRelicCreated(resp *relic.RelicCreateResponse, metadata *relic.RelicMetadata, format OutputFormat, serverURL string) error {
	switch format {
	case FormatJSON:
		return printJSON(resp)
	case FormatURL:
		fmt.Println(makeFullURL(serverURL, resp.URL))
		return nil
	default:
		return printRelicCreatedHuman(resp, metadata, serverURL)
	}
}

func printRelicCreatedHuman(resp *relic.RelicCreateResponse, metadata *relic.RelicMetadata, serverURL string) error {
	fmt.Printf("%s Created relic: %s\n", Success(SymbolSuccess), Bold(resp.ID))
	fmt.Printf("  URL: %s\n", makeFullURL(serverURL, resp.URL))

	if metadata != nil {
		if metadata.Name != "" {
			fmt.Printf("  Name: %s\n", metadata.Name)
		}
		fmt.Printf("  Size: %s\n", formatBytes(metadata.SizeBytes))
		fmt.Printf("  Type: %s\n", metadata.ContentType)
		if metadata.LanguageHint != "" {
			fmt.Printf("  Language: %s\n", metadata.LanguageHint)
		}
		fmt.Printf("  Access: %s\n", metadata.AccessLevel)
		if metadata.ExpiresAt != nil {
			fmt.Printf("  Expires: %s\n", metadata.ExpiresAt.Time.Format(time.RFC3339))
		}
	}

	return nil
}

// PrintRelicInfo prints detailed information about a relic
func PrintRelicInfo(metadata *relic.RelicMetadata, format OutputFormat) error {
	switch format {
	case FormatJSON:
		return printJSON(metadata)
	default:
		return printRelicInfoHuman(metadata)
	}
}

func printRelicInfoHuman(metadata *relic.RelicMetadata) error {
	fmt.Printf("Relic: %s\n", Bold(metadata.ID))
	if metadata.Name != "" {
		fmt.Printf("Name: %s\n", metadata.Name)
	}
	if metadata.Description != "" {
		fmt.Printf("Description: %s\n", metadata.Description)
	}
	fmt.Printf("Size: %s\n", formatBytes(metadata.SizeBytes))
	fmt.Printf("Type: %s", metadata.ContentType)
	if metadata.LanguageHint != "" {
		fmt.Printf(" (%s)", metadata.LanguageHint)
	}
	fmt.Println()
	fmt.Printf("Created: %s\n", formatTime(metadata.CreatedAt.Time))
	if metadata.ExpiresAt != nil {
		fmt.Printf("Expires: %s\n", formatTime(metadata.ExpiresAt.Time))
	}
	fmt.Printf("Access: %s\n", metadata.AccessLevel)
	fmt.Printf("Views: %d\n", metadata.AccessCount)
	if metadata.ForkOf != "" {
		fmt.Printf("Fork of: %s\n", metadata.ForkOf)
	}

	return nil
}

// PrintRelicList prints a list of relics
func PrintRelicList(list *relic.RelicListResponse, format OutputFormat, serverURL string) error {
	switch format {
	case FormatJSON:
		return printJSON(list)
	default:
		return printRelicListHuman(list, serverURL)
	}
}

func printRelicListHuman(list *relic.RelicListResponse, serverURL string) error {
	if len(list.Relics) == 0 {
		fmt.Println("No relics found")
		return nil
	}

	// Print header
	fmt.Printf("%-50s %-20s %-8s %-15s %-10s %s\n",
		"URL", "Name", "Size", "Type", "Created", "Access")
	fmt.Println("────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────")

	// Print each relic
	for _, r := range list.Relics {
		name := r.Name
		if name == "" {
			name = Muted("(unnamed)")
		}
		if len(name) > 20 {
			name = name[:17] + "..."
		}

		contentType := r.ContentType
		if len(contentType) > 15 {
			contentType = contentType[:12] + "..."
		}

		// Construct full URL
		url := makeFullURL(serverURL, "/"+r.ID)

		fmt.Printf("%-50s %-20s %-8s %-15s %-10s %s\n",
			url,
			name,
			formatBytes(r.SizeBytes),
			contentType,
			formatTimeAgo(r.CreatedAt.Time),
			r.AccessLevel,
		)
	}

	fmt.Printf("\nTotal: %d relics\n", list.Total)

	return nil
}

// PrintClientInfo prints information about the client
func PrintClientInfo(info *relic.ClientInfo, server string) error {
	fmt.Printf("Client ID: %s\n", Bold(info.ClientID))
	fmt.Printf("Server: %s\n", server)
	fmt.Printf("Registered: %s\n", formatTime(info.CreatedAt.Time))
	fmt.Printf("Relics: %d\n", info.RelicCount)

	return nil
}

// printJSON prints any data as JSON
func printJSON(data interface{}) error {
	encoder := json.NewEncoder(os.Stdout)
	encoder.SetIndent("", "  ")
	return encoder.Encode(data)
}

// formatBytes formats bytes into human-readable size
func formatBytes(bytes int64) string {
	const unit = 1024
	if bytes < unit {
		return fmt.Sprintf("%d B", bytes)
	}
	div, exp := int64(unit), 0
	for n := bytes / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %cB", float64(bytes)/float64(div), "KMGTPE"[exp])
}

// formatTime formats a timestamp
func formatTime(t time.Time) string {
	return t.Format("2006-01-02 15:04:05 MST")
}

// formatTimeAgo formats a timestamp as relative time
func formatTimeAgo(t time.Time) string {
	duration := time.Since(t)

	if duration < time.Minute {
		return "just now"
	} else if duration < time.Hour {
		mins := int(duration.Minutes())
		return fmt.Sprintf("%dm ago", mins)
	} else if duration < 24*time.Hour {
		hours := int(duration.Hours())
		return fmt.Sprintf("%dh ago", hours)
	} else if duration < 7*24*time.Hour {
		days := int(duration.Hours() / 24)
		return fmt.Sprintf("%dd ago", days)
	} else if duration < 30*24*time.Hour {
		weeks := int(duration.Hours() / 24 / 7)
		return fmt.Sprintf("%dw ago", weeks)
	} else if duration < 365*24*time.Hour {
		months := int(duration.Hours() / 24 / 30)
		return fmt.Sprintf("%dmo ago", months)
	}

	years := int(duration.Hours() / 24 / 365)
	return fmt.Sprintf("%dy ago", years)
}

// makeFullURL constructs a full URL from server and path
func makeFullURL(serverURL, path string) string {
	// Remove trailing slash from server URL
	if len(serverURL) > 0 && serverURL[len(serverURL)-1] == '/' {
		serverURL = serverURL[:len(serverURL)-1]
	}

	// Ensure path starts with /
	if len(path) > 0 && path[0] != '/' {
		path = "/" + path
	}

	return serverURL + path
}
