package ui

import "github.com/fatih/color"

var (
	// Success colors (green)
	Success = color.New(color.FgGreen).SprintFunc()

	// Error colors (red)
	Error = color.New(color.FgRed).SprintFunc()

	// Warning colors (yellow)
	Warning = color.New(color.FgYellow).SprintFunc()

	// Info colors (blue)
	Info = color.New(color.FgBlue).SprintFunc()

	// Muted colors (gray)
	Muted = color.New(color.FgHiBlack).SprintFunc()

	// Bold text
	Bold = color.New(color.Bold).SprintFunc()
)

// Symbols for different message types
const (
	SymbolSuccess = "✓"
	SymbolError   = "✗"
	SymbolWarning = "⚠"
	SymbolInfo    = "ℹ"
)
