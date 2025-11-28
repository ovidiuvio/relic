package upload

import (
	"mime"
	"net/http"
	"path/filepath"
	"strings"
)

// languageExtensions maps file extensions to language hints
var languageExtensions = map[string]string{
	".py":   "python",
	".js":   "javascript",
	".ts":   "typescript",
	".jsx":  "javascript",
	".tsx":  "typescript",
	".go":   "go",
	".rs":   "rust",
	".c":    "c",
	".cpp":  "cpp",
	".cc":   "cpp",
	".cxx":  "cpp",
	".h":    "c",
	".hpp":  "cpp",
	".java": "java",
	".rb":   "ruby",
	".php":  "php",
	".sh":   "bash",
	".bash": "bash",
	".zsh":  "zsh",
	".sql":  "sql",
	".html": "html",
	".css":  "css",
	".scss": "scss",
	".sass": "sass",
	".json": "json",
	".yaml": "yaml",
	".yml":  "yaml",
	".xml":  "xml",
	".md":   "markdown",
	".txt":  "plaintext",
}

// DetectContentType detects the MIME type from filename and content
func DetectContentType(filename string, content []byte) string {
	// Try extension-based detection first
	if filename != "" {
		ext := strings.ToLower(filepath.Ext(filename))
		if mimeType := mime.TypeByExtension(ext); mimeType != "" {
			return mimeType
		}
	}

	// Fall back to content sniffing
	if len(content) > 0 {
		return http.DetectContentType(content)
	}

	// Default
	return "text/plain"
}

// DetectLanguageHint detects the language hint from filename
func DetectLanguageHint(filename string) string {
	if filename == "" {
		return ""
	}

	ext := strings.ToLower(filepath.Ext(filename))
	if lang, ok := languageExtensions[ext]; ok {
		return lang
	}

	return ""
}
