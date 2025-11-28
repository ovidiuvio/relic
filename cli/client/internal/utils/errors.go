package utils

import (
	"fmt"
	"net/http"
	"os"
)

// Exit codes following Unix conventions
const (
	ExitSuccess         = 0
	ExitGeneralError    = 1
	ExitUsageError      = 2
	ExitNetworkError    = 3
	ExitAuthError       = 4
	ExitFileError       = 5
)

// CLIError represents a CLI error with an exit code
type CLIError struct {
	Message  string
	ExitCode int
}

func (e *CLIError) Error() string {
	return e.Message
}

// NewCLIError creates a new CLI error
func NewCLIError(message string, exitCode int) *CLIError {
	return &CLIError{
		Message:  message,
		ExitCode: exitCode,
	}
}

// HandleError prints an error and exits with the appropriate code
func HandleError(err error) {
	if err == nil {
		return
	}

	if cliErr, ok := err.(*CLIError); ok {
		fmt.Fprintf(os.Stderr, "✗ Error: %s\n", cliErr.Message)
		os.Exit(cliErr.ExitCode)
	}

	fmt.Fprintf(os.Stderr, "✗ Error: %s\n", err.Error())
	os.Exit(ExitGeneralError)
}

// IsRetryableError checks if an HTTP error is retryable
func IsRetryableError(statusCode int) bool {
	// Retry on server errors and some client errors
	switch statusCode {
	case http.StatusRequestTimeout,
		http.StatusTooManyRequests,
		http.StatusInternalServerError,
		http.StatusBadGateway,
		http.StatusServiceUnavailable,
		http.StatusGatewayTimeout:
		return true
	}
	return false
}

// GetErrorFromStatus converts HTTP status code to appropriate CLI error
func GetErrorFromStatus(statusCode int, message string) *CLIError {
	switch {
	case statusCode >= 500:
		return NewCLIError(message, ExitNetworkError)
	case statusCode == http.StatusUnauthorized || statusCode == http.StatusForbidden:
		return NewCLIError(message, ExitAuthError)
	case statusCode >= 400:
		return NewCLIError(message, ExitUsageError)
	default:
		return NewCLIError(message, ExitGeneralError)
	}
}
