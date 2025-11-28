package main

import (
	"fmt"
	"io"
	"os"
	"path/filepath"

	"github.com/relic/cli/internal/api"
	"github.com/relic/cli/internal/config"
	"github.com/relic/cli/internal/ui"
	"github.com/relic/cli/internal/upload"
	"github.com/relic/cli/internal/utils"
	"github.com/relic/cli/pkg/relic"
	"github.com/spf13/cobra"
)

var (
	// Version is the CLI version (set during build)
	Version = "0.1.0"

	// Global flags
	verbose     bool
	outputFmt   string
	quiet       bool
	noProgress  bool
	serverURL   string
	clientKey   string

	// Upload flags
	relicName    string
	description  string
	language     string
	accessLevel  string
	publicFlag   bool
	privateFlag  bool
	expiresIn    string
	password     string

	// List flags
	limit       int
	offset      int
	filterLevel string

	// Delete flags
	skipConfirm bool

	// Output file flag
	outputFile string
)

func main() {
	rootCmd := &cobra.Command{
		Use:     "relic [file]",
		Short:   "Relic - Immutable artifact storage",
		Long:    `A command-line interface for the Relic artifact storage service.`,
		Version: Version,
		RunE:    uploadCommand,
		Args:    cobra.MaximumNArgs(1),
	}

	// Global flags
	rootCmd.PersistentFlags().BoolVarP(&verbose, "verbose", "v", false, "verbose output")
	rootCmd.PersistentFlags().StringVarP(&outputFmt, "output", "o", "human", "output format (human, json, url)")
	rootCmd.PersistentFlags().BoolVarP(&quiet, "quiet", "q", false, "quiet mode (URL only)")
	rootCmd.PersistentFlags().StringVar(&serverURL, "server", "", "API server URL")
	rootCmd.PersistentFlags().StringVar(&clientKey, "client-key", "", "client authentication key")

	// Upload flags
	rootCmd.Flags().StringVarP(&relicName, "name", "n", "", "relic name")
	rootCmd.Flags().StringVarP(&description, "description", "d", "", "relic description")
	rootCmd.Flags().StringVarP(&language, "language", "l", "", "language hint for syntax highlighting")
	rootCmd.Flags().StringVarP(&accessLevel, "access-level", "a", "", "access level (public or private)")
	rootCmd.Flags().BoolVarP(&publicFlag, "public", "P", false, "make relic public")
	rootCmd.Flags().BoolVarP(&privateFlag, "private", "S", false, "make relic private/secret (default)")
	rootCmd.Flags().StringVarP(&expiresIn, "expires-in", "e", "", "expiration time (1h, 24h, 7d, 30d, never)")
	rootCmd.Flags().StringVarP(&password, "password", "p", "", "password protection")
	rootCmd.Flags().BoolVar(&noProgress, "no-progress", false, "disable progress bar")

	// Subcommands
	rootCmd.AddCommand(infoCmd())
	rootCmd.AddCommand(listCmd())
	rootCmd.AddCommand(getCmd())
	rootCmd.AddCommand(forkCmd())
	rootCmd.AddCommand(deleteCmd())
	rootCmd.AddCommand(whoamiCmd())
	rootCmd.AddCommand(initCmd())
	rootCmd.AddCommand(configCmd())
	rootCmd.AddCommand(recentCmd())
	rootCmd.AddCommand(installCmd())

	if err := rootCmd.Execute(); err != nil {
		utils.HandleError(err)
	}
}

// uploadCommand handles file/stdin upload
func uploadCommand(cmd *cobra.Command, args []string) error {
	cfg, err := loadConfig()
	if err != nil {
		return err
	}

	// Ensure client key
	key, isNew, err := api.EnsureClientKey(cfg)
	if err != nil {
		return err
	}
	cfg.ClientKey = key

	if isNew && !quiet {
		fmt.Fprintf(os.Stderr, "%s Generated new client key: %s\n", ui.Info(ui.SymbolInfo), key[:8]+"...")
		fmt.Fprintf(os.Stderr, "%s Client key saved to config\n", ui.Success(ui.SymbolSuccess))
	}

	// Build upload options
	opts := &upload.UploadOptions{
		Name:         relicName,
		Description:  description,
		Language:     language,
		AccessLevel:  getAccessLevel(cfg),
		ExpiresIn:    getExpiresIn(cfg),
		Password:     password,
		ShowProgress: !noProgress && cfg.Progress && !quiet,
		Verbose:      verbose,
	}

	// Determine output format
	format := getOutputFormat()

	var resp *relic.RelicCreateResponse

	// Check if input is from stdin or file
	if len(args) == 0 || args[0] == "-" {
		// Upload from stdin
		if !utils.IsStdin() && len(args) == 0 {
			return utils.NewCLIError("No input provided. Pipe content or specify a file.", utils.ExitUsageError)
		}
		resp, err = upload.UploadStdin(cfg, key, opts)
	} else {
		// Upload file
		resp, err = upload.UploadFile(cfg, key, args[0], opts)
	}

	if err != nil {
		return err
	}

	// Get metadata for detailed output
	var metadata *relic.RelicMetadata
	if format == ui.FormatHuman {
		apiClient := api.NewClient(cfg, verbose)
		apiClient.ClientKey = key
		metadata, _ = apiClient.GetRelic(resp.ID)
	}

	return ui.PrintRelicCreated(resp, metadata, format, cfg.Server)
}

// infoCmd returns the info command
func infoCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "info ID",
		Short: "Get information about a relic",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			cfg, err := loadConfig()
			if err != nil {
				return err
			}

			apiClient := api.NewClient(cfg, verbose)
			metadata, err := apiClient.GetRelic(args[0])
			if err != nil {
				return err
			}

			return ui.PrintRelicInfo(metadata, getOutputFormat())
		},
	}
}

// listCmd returns the list command
func listCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "list",
		Short: "List your relics",
		RunE: func(cmd *cobra.Command, args []string) error {
			cfg, err := loadConfig()
			if err != nil {
				return err
			}

			if cfg.ClientKey == "" {
				return utils.NewCLIError("Client key required. Run a command to generate one.", utils.ExitAuthError)
			}

			apiClient := api.NewClient(cfg, verbose)
			list, err := apiClient.ListClientRelics(limit, offset, filterLevel)
			if err != nil {
				return err
			}

			return ui.PrintRelicList(list, getOutputFormat(), cfg.Server)
		},
	}

	cmd.Flags().IntVar(&limit, "limit", 20, "limit results")
	cmd.Flags().IntVar(&offset, "offset", 0, "pagination offset")
	cmd.Flags().StringVar(&filterLevel, "access-level", "", "filter by access level")

	return cmd
}

// recentCmd returns the recent command
func recentCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "recent",
		Short: "List recent public relics",
		RunE: func(cmd *cobra.Command, args []string) error {
			cfg, err := loadConfig()
			if err != nil {
				return err
			}

			apiClient := api.NewClient(cfg, verbose)
			list, err := apiClient.ListRelics(limit, offset)
			if err != nil {
				return err
			}

			return ui.PrintRelicList(list, getOutputFormat(), cfg.Server)
		},
	}

	cmd.Flags().IntVar(&limit, "limit", 20, "limit results")
	cmd.Flags().IntVar(&offset, "offset", 0, "pagination offset")

	return cmd
}

// getCmd returns the get command
func getCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "get ID",
		Short: "Download relic content",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			cfg, err := loadConfig()
			if err != nil {
				return err
			}

			apiClient := api.NewClient(cfg, verbose)
			content, err := apiClient.GetRelicContent(args[0])
			if err != nil {
				return err
			}
			defer content.Close()

			// Output to file or stdout
			var output io.Writer = os.Stdout
			if outputFile != "" {
				file, err := os.Create(outputFile)
				if err != nil {
					return utils.NewCLIError(fmt.Sprintf("Failed to create output file: %v", err), utils.ExitFileError)
				}
				defer file.Close()
				output = file
			}

			_, err = io.Copy(output, content)
			return err
		},
	}

	cmd.Flags().StringVarP(&outputFile, "output", "o", "", "output file (default: stdout)")

	return cmd
}

// forkCmd returns the fork command
func forkCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "fork ID",
		Short: "Fork a relic",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			cfg, err := loadConfig()
			if err != nil {
				return err
			}

			// Ensure client key
			key, isNew, err := api.EnsureClientKey(cfg)
			if err != nil {
				return err
			}
			cfg.ClientKey = key

			if isNew && !quiet {
				fmt.Fprintf(os.Stderr, "%s Generated new client key: %s\n", ui.Info(ui.SymbolInfo), key[:8]+"...")
			}

			apiClient := api.NewClient(cfg, verbose)
			apiClient.ClientKey = key

			req := &relic.RelicCreateRequest{
				Name:        relicName,
				Description: description,
				AccessLevel: getAccessLevel(cfg),
			}

			resp, err := apiClient.ForkRelic(args[0], req)
			if err != nil {
				return err
			}

			// Get metadata for detailed output
			format := getOutputFormat()
			var metadata *relic.RelicMetadata
			if format == ui.FormatHuman {
				metadata, _ = apiClient.GetRelic(resp.ID)
			}

			return ui.PrintRelicCreated(resp, metadata, format, cfg.Server)
		},
	}

	cmd.Flags().StringVarP(&relicName, "name", "n", "", "relic name")
	cmd.Flags().StringVarP(&description, "description", "d", "", "relic description")
	cmd.Flags().StringVarP(&accessLevel, "access-level", "a", "", "access level (public or private)")

	return cmd
}

// deleteCmd returns the delete command
func deleteCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "delete ID",
		Short: "Delete a relic",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			cfg, err := loadConfig()
			if err != nil {
				return err
			}

			if cfg.ClientKey == "" {
				return utils.NewCLIError("Client key required. You must be the owner to delete.", utils.ExitAuthError)
			}

			// Confirm deletion
			if !skipConfirm {
				if !ui.Confirm(fmt.Sprintf("Delete relic %s?", args[0])) {
					fmt.Println("Cancelled")
					return nil
				}
			}

			apiClient := api.NewClient(cfg, verbose)
			if err := apiClient.DeleteRelic(args[0]); err != nil {
				return err
			}

			if !quiet {
				fmt.Printf("%s Deleted relic: %s\n", ui.Success(ui.SymbolSuccess), args[0])
			}

			return nil
		},
	}

	cmd.Flags().BoolVarP(&skipConfirm, "yes", "y", false, "skip confirmation")

	return cmd
}

// whoamiCmd returns the whoami command
func whoamiCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "whoami",
		Short: "Show client information",
		RunE: func(cmd *cobra.Command, args []string) error {
			cfg, err := loadConfig()
			if err != nil {
				return err
			}

			if cfg.ClientKey == "" {
				return utils.NewCLIError("No client key found. Create a relic to generate one.", utils.ExitAuthError)
			}

			apiClient := api.NewClient(cfg, verbose)
			info, err := apiClient.RegisterClient()
			if err != nil {
				return err
			}

			return ui.PrintClientInfo(info, cfg.Server)
		},
	}
}

// initCmd returns the init command
func initCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "init",
		Short: "Initialize configuration file",
		RunE: func(cmd *cobra.Command, args []string) error {
			if err := config.InitConfig(); err != nil {
				return err
			}

			configDir, _ := config.GetConfigDir()
			fmt.Printf("%s Created config file at %s/config\n", ui.Success(ui.SymbolSuccess), configDir)

			return nil
		},
	}
}

// configCmd returns the config command
func configCmd() *cobra.Command {
	var listConfig bool

	cmd := &cobra.Command{
		Use:   "config [key] [value]",
		Short: "Manage configuration",
		RunE: func(cmd *cobra.Command, args []string) error {
			if listConfig {
				cfg, err := config.Load()
				if err != nil {
					return err
				}

				fmt.Printf("core.server = %s\n", cfg.Server)
				fmt.Printf("core.timeout = %d\n", cfg.Timeout)
				fmt.Printf("core.progress = %t\n", cfg.Progress)
				if cfg.ClientKey != "" {
					fmt.Printf("client.key = %s...\n", cfg.ClientKey[:8])
				} else {
					fmt.Printf("client.key = (not set)\n")
				}
				fmt.Printf("defaults.access_level = %s\n", cfg.AccessLevel)
				fmt.Printf("defaults.expires_in = %s\n", cfg.ExpiresIn)

				return nil
			}

			if len(args) == 0 {
				return utils.NewCLIError("Usage: relic config [key] [value] or relic config --list", utils.ExitUsageError)
			}

			if len(args) == 1 {
				// Get single value
				cfg, err := config.Load()
				if err != nil {
					return err
				}

				switch args[0] {
				case "core.server", "server":
					fmt.Println(cfg.Server)
				case "client.key", "key":
					if cfg.ClientKey != "" {
						fmt.Println(cfg.ClientKey)
					}
				case "core.timeout", "timeout":
					fmt.Println(cfg.Timeout)
				case "defaults.access_level", "access_level":
					fmt.Println(cfg.AccessLevel)
				case "defaults.expires_in", "expires_in":
					fmt.Println(cfg.ExpiresIn)
				default:
					return utils.NewCLIError(fmt.Sprintf("Unknown config key: %s", args[0]), utils.ExitUsageError)
				}

				return nil
			}

			// Set value
			if err := config.Save(args[0], args[1]); err != nil {
				return err
			}

			fmt.Printf("%s Set %s = %s\n", ui.Success(ui.SymbolSuccess), args[0], args[1])

			return nil
		},
	}

	cmd.Flags().BoolVar(&listConfig, "list", false, "list all config values")

	return cmd
}

// installCmd returns the install command
func installCmd() *cobra.Command {
	var installPath string

	cmd := &cobra.Command{
		Use:   "install",
		Short: "Install relic binary to system path",
		Long: `Install the relic binary to a system path (default: /usr/local/bin).
This allows you to run 'relic' from anywhere without specifying the full path.

Note: You may need sudo privileges to install to system directories.`,
		RunE: func(cmd *cobra.Command, args []string) error {
			// Get current executable path
			exePath, err := os.Executable()
			if err != nil {
				return utils.NewCLIError(fmt.Sprintf("Failed to get executable path: %v", err), utils.ExitGeneralError)
			}

			// Default install path
			if installPath == "" {
				installPath = "/usr/local/bin/relic"
			}

			// Check if we need sudo
			if _, err := os.Stat(filepath.Dir(installPath)); err != nil {
				return utils.NewCLIError(fmt.Sprintf("Install directory does not exist: %s", filepath.Dir(installPath)), utils.ExitFileError)
			}

			// Try to copy the file
			if !quiet {
				fmt.Printf("Installing %s to %s...\n", filepath.Base(exePath), installPath)
			}

			// Read current executable
			data, err := os.ReadFile(exePath)
			if err != nil {
				return utils.NewCLIError(fmt.Sprintf("Failed to read executable: %v", err), utils.ExitFileError)
			}

			// Write to install path
			if err := os.WriteFile(installPath, data, 0755); err != nil {
				if os.IsPermission(err) {
					return utils.NewCLIError(
						fmt.Sprintf("Permission denied. Try running with sudo:\n  sudo %s install", exePath),
						utils.ExitFileError,
					)
				}
				return utils.NewCLIError(fmt.Sprintf("Failed to install: %v", err), utils.ExitFileError)
			}

			if !quiet {
				fmt.Printf("%s Successfully installed to %s\n", ui.Success(ui.SymbolSuccess), installPath)
				fmt.Printf("%s You can now run 'relic' from anywhere\n", ui.Info(ui.SymbolInfo))
			}

			return nil
		},
	}

	cmd.Flags().StringVar(&installPath, "path", "", "installation path (default: /usr/local/bin/relic)")

	return cmd
}

// Helper functions

func loadConfig() (*config.Config, error) {
	cfg, err := config.Load()
	if err != nil {
		return nil, err
	}

	// Override from command-line flags
	if serverURL != "" {
		cfg.Server = serverURL
	}
	if clientKey != "" {
		cfg.ClientKey = clientKey
	}

	return cfg, nil
}

func getOutputFormat() ui.OutputFormat {
	if quiet {
		return ui.FormatURL
	}
	switch outputFmt {
	case "json":
		return ui.FormatJSON
	case "url":
		return ui.FormatURL
	default:
		return ui.FormatHuman
	}
}

func getAccessLevel(cfg *config.Config) string {
	// Flags take precedence over config
	if publicFlag {
		return "public"
	}
	if privateFlag {
		return "private"
	}
	if accessLevel != "" {
		return accessLevel
	}
	return cfg.AccessLevel
}

func getExpiresIn(cfg *config.Config) string {
	if expiresIn != "" {
		return expiresIn
	}
	return cfg.ExpiresIn
}
