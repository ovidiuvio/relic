package ui

import "github.com/fatih/color"

var (
	// Success colors (green)
	Success = color.New(color.FgGreen).SprintFunc()
	SuccessBold = color.New(color.FgGreen, color.Bold).SprintFunc()

	// Error colors (red)
	Error = color.New(color.FgRed).SprintFunc()
	ErrorBold = color.New(color.FgRed, color.Bold).SprintFunc()

	// Warning colors (yellow)
	Warning = color.New(color.FgYellow).SprintFunc()
	WarningBold = color.New(color.FgYellow, color.Bold).SprintFunc()

	// Info colors (blue/cyan)
	Info = color.New(color.FgBlue).SprintFunc()
	InfoBold = color.New(color.FgBlue, color.Bold).SprintFunc()
	Cyan = color.New(color.FgCyan).SprintFunc()
	CyanBold = color.New(color.FgCyan, color.Bold).SprintFunc()

	// Muted colors (gray)
	Muted = color.New(color.FgHiBlack).SprintFunc()

	// Bold text
	Bold = color.New(color.Bold).SprintFunc()

	// Magenta for special highlights
	Magenta = color.New(color.FgMagenta).SprintFunc()
	MagentaBold = color.New(color.FgMagenta, color.Bold).SprintFunc()

	// White bold for emphasis
	WhiteBold = color.New(color.FgWhite, color.Bold).SprintFunc()
)

// Symbols for different message types
const (
	SymbolSuccess = "✓"
	SymbolError   = "✗"
	SymbolWarning = "⚠"
	SymbolInfo    = "ℹ"
	SymbolRocket  = "🚀"
	SymbolLink    = "🔗"
	SymbolFile    = "📄"
	SymbolFolder  = "📁"
	SymbolPublic  = "🌐"
	SymbolPrivate = "🔒"
	SymbolClock   = "🕐"
	SymbolSize    = "📊"
	SymbolArrow   = "→"
	SymbolCheck   = "✔"
	SymbolDot     = "•"
)
