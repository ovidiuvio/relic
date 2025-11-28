package config

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/spf13/viper"
)

// Config represents the CLI configuration
type Config struct {
	Server      string
	ClientKey   string
	Timeout     int
	Progress    bool
	AccessLevel string
	ExpiresIn   string
}

// Load loads the configuration from file and environment variables
func Load() (*Config, error) {
	// Get config directory
	configDir, err := GetConfigDir()
	if err != nil {
		return nil, fmt.Errorf("failed to get config directory: %w", err)
	}

	// Set up viper
	viper.SetConfigName(ConfigFileName)
	viper.SetConfigType("ini")
	viper.AddConfigPath(configDir)

	// Set defaults
	viper.SetDefault("core.server", DefaultServer)
	viper.SetDefault("core.timeout", DefaultTimeout)
	viper.SetDefault("core.progress", DefaultProgress)
	viper.SetDefault("defaults.access_level", DefaultAccessLevel)
	viper.SetDefault("defaults.expires_in", DefaultExpiresIn)

	// Environment variables (with RELIC_ prefix)
	viper.SetEnvPrefix("RELIC")
	viper.AutomaticEnv()

	// Map environment variables to config keys
	viper.BindEnv("core.server", "RELIC_SERVER")
	viper.BindEnv("client.key", "RELIC_CLIENT_KEY")
	viper.BindEnv("core.timeout", "RELIC_TIMEOUT")
	viper.BindEnv("core.progress", "RELIC_PROGRESS")
	viper.BindEnv("defaults.access_level", "RELIC_ACCESS_LEVEL")
	viper.BindEnv("defaults.expires_in", "RELIC_EXPIRES_IN")

	// Read config file (ignore error if file doesn't exist)
	if err := viper.ReadInConfig(); err != nil {
		if _, ok := err.(viper.ConfigFileNotFoundError); !ok {
			return nil, fmt.Errorf("failed to read config file: %w", err)
		}
	}

	// Build config struct
	cfg := &Config{
		Server:      viper.GetString("core.server"),
		ClientKey:   viper.GetString("client.key"),
		Timeout:     viper.GetInt("core.timeout"),
		Progress:    viper.GetBool("core.progress"),
		AccessLevel: viper.GetString("defaults.access_level"),
		ExpiresIn:   viper.GetString("defaults.expires_in"),
	}

	return cfg, nil
}

// Save saves a configuration value to the config file
func Save(key, value string) error {
	// Get config directory
	configDir, err := GetConfigDir()
	if err != nil {
		return fmt.Errorf("failed to get config directory: %w", err)
	}

	// Ensure config directory exists
	if err := os.MkdirAll(configDir, 0700); err != nil {
		return fmt.Errorf("failed to create config directory: %w", err)
	}

	configPath := filepath.Join(configDir, ConfigFileName)

	// Read existing config or create new
	viper.SetConfigFile(configPath)
	viper.SetConfigType("ini")

	// Try to read existing config (ignore error if doesn't exist)
	viper.ReadInConfig()

	// Set the value
	viper.Set(key, value)

	// Write config file
	if err := viper.WriteConfig(); err != nil {
		// If file doesn't exist, create it
		if os.IsNotExist(err) {
			if err := viper.SafeWriteConfig(); err != nil {
				return fmt.Errorf("failed to write config: %w", err)
			}
		} else {
			return fmt.Errorf("failed to write config: %w", err)
		}
	}

	return nil
}

// GetConfigDir returns the path to the config directory
func GetConfigDir() (string, error) {
	homeDir, err := os.UserHomeDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(homeDir, ConfigDirName), nil
}

// InitConfig creates a default config file
func InitConfig() error {
	configDir, err := GetConfigDir()
	if err != nil {
		return fmt.Errorf("failed to get config directory: %w", err)
	}

	// Ensure config directory exists
	if err := os.MkdirAll(configDir, 0700); err != nil {
		return fmt.Errorf("failed to create config directory: %w", err)
	}

	configPath := filepath.Join(configDir, ConfigFileName)

	// Check if config already exists
	if _, err := os.Stat(configPath); err == nil {
		return fmt.Errorf("config file already exists at %s", configPath)
	}

	// Create default config content
	configContent := fmt.Sprintf(`[core]
    server = %s
    timeout = %d
    progress = %t

[client]
    key =

[defaults]
    access_level = %s
    expires_in = %s
`, DefaultServer, DefaultTimeout, DefaultProgress, DefaultAccessLevel, DefaultExpiresIn)

	// Write config file with secure permissions
	if err := os.WriteFile(configPath, []byte(configContent), 0600); err != nil {
		return fmt.Errorf("failed to create config file: %w", err)
	}

	return nil
}
