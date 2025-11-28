package config

const (
	// DefaultServer is the default Relic API server URL
	DefaultServer = "http://localhost:8000"

	// DefaultTimeout is the default HTTP timeout in seconds
	DefaultTimeout = 30

	// DefaultAccessLevel is the default access level for relics
	DefaultAccessLevel = "private"

	// DefaultExpiresIn is the default expiration time
	DefaultExpiresIn = "never"

	// DefaultProgress controls whether to show progress bars
	DefaultProgress = true

	// ConfigFileName is the name of the config file
	ConfigFileName = "config"

	// ConfigDirName is the name of the config directory
	ConfigDirName = ".relic"

	// MaxFileSize is the maximum file size in bytes (100MB)
	MaxFileSize = 100 * 1024 * 1024
)
