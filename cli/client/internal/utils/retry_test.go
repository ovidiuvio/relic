package utils

import (
	"testing"
	"time"
)

func TestShouldRetry(t *testing.T) {
	tests := []struct {
		attempt  int
		expected bool
	}{
		{0, true},
		{1, true},
		{2, true},
		{3, false},
		{4, false},
	}

	for _, tt := range tests {
		actual := ShouldRetry(tt.attempt)
		if actual != tt.expected {
			t.Errorf("ShouldRetry(%d): expected %t, got %t", tt.attempt, tt.expected, actual)
		}
	}
}

func TestRetryBackoff(t *testing.T) {
	backoffs := RetryBackoff()
	expected := []time.Duration{
		1 * time.Second,
		2 * time.Second,
		4 * time.Second,
	}

	if len(backoffs) != len(expected) {
		t.Fatalf("RetryBackoff length: expected %d, got %d", len(expected), len(backoffs))
	}

	for i, v := range expected {
		if backoffs[i] != v {
			t.Errorf("RetryBackoff()[%d]: expected %s, got %s", i, v, backoffs[i])
		}
	}
}
