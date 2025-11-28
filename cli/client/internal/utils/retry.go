package utils

import (
	"time"
)

const (
	// MaxRetries is the maximum number of retry attempts
	MaxRetries = 3
)

// RetryBackoff returns the backoff durations for retries
func RetryBackoff() []time.Duration {
	return []time.Duration{
		1 * time.Second,
		2 * time.Second,
		4 * time.Second,
	}
}

// ShouldRetry checks if we should retry based on attempt number
func ShouldRetry(attempt int) bool {
	return attempt < MaxRetries
}
