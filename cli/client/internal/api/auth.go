package api

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"

	"github.com/relic/cli/internal/config"
)

// GenerateUserKey generates a new random user key
func GenerateUserKey() (string, error) {
	bytes := make([]byte, 16) // 32 hex characters
	if _, err := rand.Read(bytes); err != nil {
		return "", fmt.Errorf("failed to generate random key: %w", err)
	}
	return hex.EncodeToString(bytes), nil
}

// EnsureUserKey ensures a user key exists, generating one in memory if needed.
// It does NOT persist a newly generated key to disk - the caller must do that
// (via config.Save) only after the key has been successfully registered with the
// server, so a failed registration doesn't leave an unregistered key permanently
// cached in the local config.
func EnsureUserKey(cfg *config.Config) (string, bool, error) {
	// If user key already exists, return it
	if cfg.UserKey != "" {
		return cfg.UserKey, false, nil
	}

	// Generate new user key
	userKey, err := GenerateUserKey()
	if err != nil {
		return "", false, err
	}

	return userKey, true, nil
}
