package api

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"

	"github.com/relic/cli/internal/config"
)

// GenerateClientKey generates a new random client key
func GenerateClientKey() (string, error) {
	bytes := make([]byte, 16) // 32 hex characters
	if _, err := rand.Read(bytes); err != nil {
		return "", fmt.Errorf("failed to generate random key: %w", err)
	}
	return hex.EncodeToString(bytes), nil
}

// EnsureClientKey ensures a client key exists, generating one if needed
func EnsureClientKey(cfg *config.Config) (string, bool, error) {
	// If client key already exists, return it
	if cfg.ClientKey != "" {
		return cfg.ClientKey, false, nil
	}

	// Generate new client key
	clientKey, err := GenerateClientKey()
	if err != nil {
		return "", false, err
	}

	// Save to config
	if err := config.Save("client.key", clientKey); err != nil {
		return "", false, fmt.Errorf("failed to save client key: %w", err)
	}

	return clientKey, true, nil
}
