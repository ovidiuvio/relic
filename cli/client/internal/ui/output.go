package ui

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"
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
	// Header
	fmt.Println()
	fmt.Printf("%s %s\n", SuccessBold(SymbolRocket), SuccessBold("Relic Created Successfully!"))
	fmt.Println(Muted("─────────────────────────────────────────────────────────"))

	// URL (most important, highlighted)
	url := makeFullURL(serverURL, resp.URL)
	fmt.Printf("%s %s\n", CyanBold(SymbolLink), CyanBold(url))
	fmt.Println()

	// Metadata
	if metadata != nil {
		if metadata.Name != "" {
			fmt.Printf("%s %s %s\n", Muted(SymbolFile), Bold("Name:"), metadata.Name)
		}
		fmt.Printf("%s %s %s\n", Muted(SymbolSize), Bold("Size:"), WhiteBold(formatBytes(metadata.SizeBytes)))
		fmt.Printf("%s %s %s\n", Muted(SymbolDot), Bold("Type:"), Muted(metadata.ContentType))
		if metadata.LanguageHint != "" {
			fmt.Printf("%s %s %s\n", Muted(SymbolDot), Bold("Language:"), metadata.LanguageHint)
		}

		// Access level with icon
		accessIcon := SymbolPrivate
		accessColor := Warning
		if metadata.AccessLevel == "public" {
			accessIcon = SymbolPublic
			accessColor = Info
		}
		fmt.Printf("%s %s %s\n", accessColor(accessIcon), Bold("Access:"), accessColor(metadata.AccessLevel))

		if metadata.ExpiresAt != nil {
			fmt.Printf("%s %s %s\n", Muted(SymbolClock), Bold("Expires:"), formatTime(metadata.ExpiresAt.Time))
		}
	}

	fmt.Println(Muted("─────────────────────────────────────────────────────────"))
	fmt.Println()

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
	fmt.Println()
	fmt.Printf("%s %s\n", InfoBold(SymbolFile), InfoBold("Relic Information"))
	fmt.Println(Muted("─────────────────────────────────────────────────────────"))
	fmt.Println()

	// ID
	fmt.Printf("%s %s\n", Muted("ID:"), CyanBold(metadata.ID))

	if metadata.Name != "" {
		fmt.Printf("%s %s %s\n", Muted(SymbolFile), Bold("Name:"), metadata.Name)
	}
	if metadata.Description != "" {
		fmt.Printf("%s %s %s\n", Muted(SymbolDot), Bold("Description:"), metadata.Description)
	}

	fmt.Printf("%s %s %s\n", Muted(SymbolSize), Bold("Size:"), WhiteBold(formatBytes(metadata.SizeBytes)))
	fmt.Printf("%s %s %s", Muted(SymbolDot), Bold("Type:"), Muted(metadata.ContentType))
	if metadata.LanguageHint != "" {
		fmt.Printf(" %s", Cyan("("+metadata.LanguageHint+")"))
	}
	fmt.Println()

	fmt.Printf("%s %s %s\n", Muted(SymbolClock), Bold("Created:"), formatTime(metadata.CreatedAt.Time))
	if metadata.ExpiresAt != nil {
		fmt.Printf("%s %s %s\n", Muted(SymbolClock), Bold("Expires:"), Warning(formatTime(metadata.ExpiresAt.Time)))
	}

	// Access level with icon
	accessIcon := SymbolPrivate
	accessColor := Warning
	if metadata.AccessLevel == "public" {
		accessIcon = SymbolPublic
		accessColor = Info
	}
	fmt.Printf("%s %s %s\n", accessColor(accessIcon), Bold("Access:"), accessColor(metadata.AccessLevel))

	fmt.Printf("%s %s %s\n", Muted("👁"), Bold("Views:"), fmt.Sprintf("%d", metadata.AccessCount))

	if metadata.ForkOf != "" {
		fmt.Printf("%s %s %s\n", Muted("🍴"), Bold("Fork of:"), metadata.ForkOf)
	}

	fmt.Println()
	fmt.Println(Muted("─────────────────────────────────────────────────────────"))
	fmt.Println()

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
		fmt.Println()
		fmt.Printf("%s %s\n", Muted(SymbolInfo), "No relics found")
		fmt.Println()
		return nil
	}

	fmt.Println()
	fmt.Printf("%s %s\n", InfoBold(SymbolFolder), InfoBold("Your Relics"))
	fmt.Println(Muted("═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════"))

	// Print header (without colors for proper alignment)
	fmt.Printf("%-50s %-20s %-10s %-18s %-12s %-6s\n",
		"URL", "Name", "Size", "Type", "Created", "Access")
	fmt.Println(Muted("─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────"))

	// Print each relic
	for _, r := range list.Relics {
		// Format name
		name := r.Name
		if name == "" {
			name = "(unnamed)"
		}
		if len(name) > 20 {
			name = name[:17] + "..."
		}

		// Format content type - use friendly names
		contentType := friendlyContentType(r.ContentType)
		if len(contentType) > 18 {
			contentType = contentType[:15] + "..."
		}

		// Construct full URL
		url := makeFullURL(serverURL, "/"+r.ID)
		if len(url) > 50 {
			url = url[:47] + "..."
		}

		// Access icon
		accessIcon := SymbolPrivate
		if r.AccessLevel == "public" {
			accessIcon = SymbolPublic
		}

		// Format and print the row with proper spacing
		urlField := fmt.Sprintf("%-50s", url)
		nameField := fmt.Sprintf("%-20s", name)
		sizeField := fmt.Sprintf("%-10s", formatBytes(r.SizeBytes))
		typeField := fmt.Sprintf("%-18s", contentType)
		timeField := fmt.Sprintf("%-12s", formatTimeAgo(r.CreatedAt.Time))

		// Print with colors applied to each field
		fmt.Printf("%s %s %s %s %s %s\n",
			Cyan(urlField),
			nameField,
			Muted(sizeField),
			Muted(typeField),
			Muted(timeField),
			accessIcon,
		)
	}

	fmt.Println(Muted("─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────"))
	fmt.Printf("%s %s %s\n", Muted(SymbolDot), Bold("Total:"), WhiteBold(fmt.Sprintf("%d relics", len(list.Relics))))
	fmt.Println()

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

// friendlyContentType converts MIME types to friendly display names
func friendlyContentType(contentType string) string {
	// Trim whitespace
	contentType = strings.TrimSpace(contentType)

	// Common text types
	if contentType == "text/plain" || contentType == "text/plain; charset=utf-8" {
		return "Text"
	}
	if contentType == "text/markdown" || contentType == "markdown" ||
	   contentType == "text/x-markdown" || strings.Contains(contentType, "markdown") {
		return "Markdown"
	}
	if contentType == "text/html" {
		return "HTML"
	}
	if contentType == "text/css" {
		return "CSS"
	}
	if contentType == "text/csv" {
		return "CSV"
	}
	if contentType == "text/xml" {
		return "XML"
	}

	// Application types
	if contentType == "application/json" {
		return "JSON"
	}
	if contentType == "application/xml" {
		return "XML"
	}
	if contentType == "application/pdf" {
		return "PDF"
	}
	if contentType == "application/zip" {
		return "ZIP Archive"
	}
	if contentType == "application/x-tar" {
		return "TAR Archive"
	}
	if contentType == "application/gzip" {
		return "GZIP Archive"
	}

	// Programming languages
	if contentType == "text/x-python" {
		return "Python"
	}
	if contentType == "text/x-go" {
		return "Go"
	}
	if contentType == "text/x-java" {
		return "Java"
	}
	if contentType == "text/x-c" {
		return "C"
	}
	if contentType == "text/x-c++" {
		return "C++"
	}
	if contentType == "text/x-rust" {
		return "Rust"
	}
	if contentType == "text/x-javascript" || contentType == "application/javascript" {
		return "JavaScript"
	}
	if contentType == "text/x-typescript" {
		return "TypeScript"
	}
	if contentType == "text/x-ruby" {
		return "Ruby"
	}
	if contentType == "text/x-php" {
		return "PHP"
	}
	if contentType == "text/x-shell" || contentType == "text/x-sh" {
		return "Shell Script"
	}

	// Image types
	if contentType == "image/png" {
		return "PNG Image"
	}
	if contentType == "image/jpeg" {
		return "JPEG Image"
	}
	if contentType == "image/gif" {
		return "GIF Image"
	}
	if contentType == "image/svg+xml" {
		return "SVG Image"
	}
	if contentType == "image/webp" {
		return "WebP Image"
	}

	// Video types
	if contentType == "video/mp4" {
		return "MP4 Video"
	}
	if contentType == "video/webm" {
		return "WebM Video"
	}

	// Audio types
	if contentType == "audio/mpeg" {
		return "MP3 Audio"
	}
	if contentType == "audio/wav" {
		return "WAV Audio"
	}

	// For unknown types, try to extract a readable part
	// e.g., "application/octet-stream" -> "octet-stream"
	if len(contentType) > 18 {
		// Try to extract the subtype after "/"
		parts := strings.Split(contentType, "/")
		if len(parts) >= 2 {
			subtype := parts[1]
			// Remove charset and other parameters
			if idx := strings.Index(subtype, ";"); idx != -1 {
				subtype = subtype[:idx]
			}
			if len(subtype) <= 18 {
				return subtype
			}
		}
		// If still too long, truncate
		return contentType[:15] + "..."
	}

	return contentType
}
