package utils

import (
	"net/http"
	"testing"
)

func TestIsRetryableError(t *testing.T) {
	tests := []struct {
		statusCode int
		expected   bool
	}{
		{http.StatusOK, false},
		{http.StatusBadRequest, false},
		{http.StatusUnauthorized, false},
		{http.StatusForbidden, false},
		{http.StatusNotFound, false},
		{http.StatusRequestTimeout, true},
		{http.StatusTooManyRequests, true},
		{http.StatusInternalServerError, true},
		{http.StatusBadGateway, true},
		{http.StatusServiceUnavailable, true},
		{http.StatusGatewayTimeout, true},
	}

	for _, tt := range tests {
		actual := IsRetryableError(tt.statusCode)
		if actual != tt.expected {
			t.Errorf("IsRetryableError(%d): expected %t, got %t", tt.statusCode, tt.expected, actual)
		}
	}
}

func TestGetErrorFromStatus(t *testing.T) {
	tests := []struct {
		statusCode       int
		message          string
		expectedExitCode int
	}{
		{http.StatusInternalServerError, "Internal Server Error", ExitNetworkError},
		{http.StatusBadGateway, "Bad Gateway", ExitNetworkError},
		{http.StatusUnauthorized, "Unauthorized", ExitAuthError},
		{http.StatusForbidden, "Forbidden", ExitAuthError},
		{http.StatusBadRequest, "Bad Request", ExitUsageError},
		{http.StatusNotFound, "Not Found", ExitUsageError},
		{http.StatusOK, "Success", ExitGeneralError}, // Status OK is not expected to represent an error, falls back to general
	}

	for _, tt := range tests {
		cliErr := GetErrorFromStatus(tt.statusCode, tt.message)
		if cliErr.ExitCode != tt.expectedExitCode {
			t.Errorf("GetErrorFromStatus(%d): expected exit code %d, got %d", tt.statusCode, tt.expectedExitCode, cliErr.ExitCode)
		}
		if cliErr.Message != tt.message {
			t.Errorf("GetErrorFromStatus(%d): expected message %q, got %q", tt.statusCode, tt.message, cliErr.Message)
		}
	}
}
