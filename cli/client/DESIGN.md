# Relic CLI Client - Design Specification

## Overview

A command-line interface for the Relic artifact storage service that follows Unix/Linux conventions and integrates seamlessly with existing tooling. The CLI enables direct piping of content from terminal commands into immutable relics with comprehensive file management capabilities.

## Command Structure & Interface

Following Unix conventions, the CLI focuses on simplicity with minimal subcommands:

```bash
# Primary usage - create relics
relic [filename]                        # Upload file or use stdin
cat data.json | relic                   # Pipe content to create relic
relic script.py                         # Upload specific file
```

## Architecture Design

### Configuration System

Following Git/Linux standards:

**Config file locations:**
 `$HOME/.relic/config` (user-level)

**Config file format (INI-style like git config):**
```ini
[core]
    server = https://api.relic.example.com
    timeout = 30
    progress = true

[client]
    key = f47ac10b58cc4372a5670e02b2c3d479

[defaults]
    access_level = private
    expires_in = never
    language_hint = auto
```

**Environment variables (override config):**
- `RELIC_SERVER` - API server URL
- `RELIC_CLIENT_KEY` - Client authentication key
- `RELIC_TIMEOUT` - Request timeout
- `RELIC_ACCESS_LEVEL` - Default access level (`public`/`private`)
- `RELIC_EXPIRES_IN` - Default expiration

### File Streaming & stdin Handling

**Simple Unix-style input methods:**

```bash
# Primary usage patterns
echo "Hello World" | relic                 # Pipe creates relic
cat data.json | relic                      # Pipe with auto-detection
relic file.txt                             # Direct file upload
git log | relic                            # Pipe command output
relic -                                    # Explicit stdin (echo | relic -)

# Advanced piping
ps aux | relic --name "processes.txt"      # Custom name
curl -s api/data | relic --name "api.json" # Download and store
```

**Stream handling strategy:**
- Detect if stdin is TTY or pipe
- For pipes: stream directly without temporary files
- For files: use streaming upload with progress
- Auto-detect MIME type from content when no filename
- Fallback to `text/plain` when content type unknown
- Single argument simplicity - no complex subcommand structure

### Authentication & Client Management

**Client key management following SSH/GPG patterns:**

```bash
# Auto-generate client key on first use
relic file.txt
# -> "No client key found. Generated client key: f47ac10b..."
# -> "Client key saved to ~/.relic/config"

# Show current client identity
relic --whoami
# -> "Client ID: f47ac10b58cc4372a5670e02b2c3d479"
# -> "Server: https://api.relic.example.com"
# -> "Relics: 42"

# Manual client key management
relic --config client.key <new_key>
export RELIC_CLIENT_KEY=<key>
```

### User Experience & Progress Indicators

**Progress bars following curl/wget style:**

```bash
$ relic large-file.zip
Upload: 100%|████████████████████| 85.2MB/85.2MB [00:03<00:00, 24.1MB/s]
✓ Created relic: https://relic.example.com/a3Bk9Zx

$ echo "big data" | relic --name "pipeline.txt"
Streaming from stdin: 100%|████████| 1.2KB/1.2KB [00:00<00:00, 5.8MB/s]
✓ Created relic: https://relic.example.com/x7Yz8Wx
```

**Output verbosity levels:**
- `--quiet` / `-q`: Only show relic URL on success
- `--verbose` / `-v`: Show full HTTP request/response details
- Default: Progress bar + essential info

**Colored output following Git conventions:**
- Green ✓ for success
- Red ✗ for errors
- Yellow ⚠ for warnings
- Blue ℹ for info

**Interactive prompts when needed:**
- Password input for protected relics
- Confirmation for destructive operations (delete)

### Output Formatting & Response Handling

**Default human-readable output:**
```bash
$ relic script.py
✓ Created relic: a3Bk9Zx
  Name: script.py
  Size: 2.1KB
  Type: text/x-python
  URL: https://relic.example.com/a3Bk9Zx
  Access: private

$ relic --info a3Bk9Zx
Relic: a3Bk9Zx
Name: script.py
Size: 2.1KB
Type: text/x-python (Python)
Created: 2024-01-15 14:23:10 UTC
Access: private
Downloads: 3
Forks: 1
```

**Machine-readable output options:**
```bash
# JSON output for scripting
relic script.py --output json
# -> {"id": "a3Bk9Zx", "url": "https://relic.example.com/a3Bk9Zx", ...}

# URL-only output for piping
relic script.py --output url
# -> https://relic.example.com/a3Bk9Zx

# Custom formatting
relic --list --format "{id} {name} {size}"
# -> a3Bk9Zx script.py 2.1KB
```

**List command with table output:**
```bash
$ relic --list --limit 5
ID          Name            Size    Type        Created    Access
a3Bk9Zx     script.py       2.1KB   Python      2m ago     private
x7Yz8Wx     data.json       15.2KB  JSON        1h ago     public
y8Za9Xy     README.md       4.8KB   Markdown    3h ago     public
```

### Error Handling & Recovery

**Exit codes following Unix conventions:**
- `0` - Success
- `1` - General error
- `2` - Usage/command line error
- `3` - Network/server error
- `4` - Authentication error
- `5` - File I/O error

**Error message format:**
```bash
$ relic missing.txt
✗ Error: File not found: missing.txt

$ relic too-large.zip
✗ Error: File too large: 150MB (limit: 100MB)

$ relic --delete a3Bk9Zx
✗ Error: Authentication required. Run 'relic --whoami' to check client key.

$ relic file.txt --server https://invalid.example.com
✗ Error: Connection failed: Unable to reach server
```

**Retry mechanisms:**
- Automatic retry for network failures (max 3 attempts)
- Exponential backoff: 1s, 2s, 4s delays
- User prompt for manual retry on auth failures
- Resume interrupted uploads if server supports it

## Advanced Features

### Pipeline Integration

**Simple piping workflows:**
```bash
# Process and upload
cat script.py | sed 's/old/new/g' | relic --name "fixed-script.py"

# Download and store
curl -s https://api.github.com/users | relic --name "users.json"

# Backup with timestamp
tar -czf - ./data | relic --name "backup-$(date +%Y%m%d).tar.gz"

# Command capture
ps aux | relic --name "processes.txt"
git log | relic --name "commit-history.txt"

# Chain operations (using external tools)
relic --info a3Bk9Zx --output json | jq '.id' | xargs -I {} relic --delete {}
```

### Batch Operations

**Multiple file handling:**
```bash
# Upload multiple files
find . -name "*.py" -exec relic {} \;

# Upload with custom settings
find . -name "*.log" -exec relic {} --access-level private --expires-in 24h \;

# Process multiple relics
for file in *.txt; do
    echo "Processing $file"
    relic "$file" --output url >> urls.txt
done
```

## Technical Implementation

### Technology Stack

**Language**: Go 1.21+
- High performance and efficient memory usage
- Single binary distribution (no dependencies)
- Excellent concurrency for parallel uploads
- Cross-platform support (Linux, macOS, Windows)

**Key Dependencies**:
- `github.com/spf13/cobra` - CLI framework and command structure
- `github.com/spf13/viper` - Configuration management (supports INI, env vars)
- `github.com/schollz/progressbar/v3` - Progress bars for uploads
- `github.com/fatih/color` - Terminal color output
- Standard library HTTP client with streaming support
- `mime` package for content type detection
- `os/user` for home directory detection

### Project Structure

```
cli/client/
├── cmd/
│   └── relic/
│       └── main.go                 # Entry point, cobra command setup
├── internal/
│   ├── api/
│   │   ├── client.go              # HTTP client wrapper
│   │   ├── relics.go              # Relic CRUD operations
│   │   └── auth.go                # Client key management
│   ├── config/
│   │   ├── config.go              # Config file management
│   │   ├── defaults.go            # Default values
│   │   └── validate.go            # Config validation
│   ├── upload/
│   │   ├── stream.go              # File/stdin streaming
│   │   ├── progress.go            # Progress tracking
│   │   └── mime.go                # Content type detection
│   ├── ui/
│   │   ├── output.go              # Human/JSON/URL formatters
│   │   ├── table.go               # Table output for lists
│   │   ├── colors.go              # Color constants
│   │   └── prompts.go             # Interactive prompts
│   └── utils/
│       ├── errors.go              # Error handling
│       ├── retry.go               # Retry logic
│       └── stdin.go               # TTY detection
├── pkg/
│   └── relic/
│       └── types.go               # Shared types (RelicMetadata, etc.)
├── bin/                           # Compiled binaries
├── go.mod
├── go.sum
├── Makefile
├── README.md
└── DESIGN.md                      # This file
```

## Complete Command Reference

### Core Commands

```bash
# Upload/Create
relic [FILE]                       # Upload file or read from stdin
  -n, --name NAME                  # Set relic name (default: filename or "stdin")
  -d, --description DESC           # Set description
  -l, --language LANG              # Set language hint (auto-detected if not set)
  -a, --access-level LEVEL         # public or private (default: private)
  -e, --expires-in DURATION        # 1h, 24h, 7d, 30d, never (default: never)
  -p, --password PASSWORD          # Set password protection
  -o, --output FORMAT              # Output format: human, json, url (default: human)
  -q, --quiet                      # Quiet mode (URL only)
  -v, --verbose                    # Verbose HTTP logging
  --no-progress                    # Disable progress bar

# Information & Listing
relic --info ID                    # Get relic metadata
  -o, --output FORMAT              # Output format: human, json

relic --list                       # List user's relics (requires client key)
  --limit N                        # Limit results (default: 20)
  --offset N                       # Pagination offset
  --access-level LEVEL             # Filter by access level
  --format TEMPLATE                # Custom output format

relic --recent                     # List recent public relics
  --limit N                        # Limit results (default: 20)

# Download
relic --get ID                     # Download relic content to stdout
  -o, --output FILE                # Save to file instead
  --password PASSWORD              # Password if protected

# Fork
relic --fork ID                    # Fork a relic
  -n, --name NAME                  # New relic name
  -d, --description DESC           # New description
  -a, --access-level LEVEL         # Access level for fork
  --password PASSWORD              # Password if source is protected

# Delete
relic --delete ID                  # Delete relic (soft delete)
  -y, --yes                        # Skip confirmation prompt

# Client Management
relic --whoami                     # Show current client identity
relic --config KEY VALUE           # Set config value
  relic --config client.key NEW_KEY
  relic --config server URL
  relic --config defaults.access_level public

# General
relic --help                       # Show help
relic --version                    # Show version
```

### Configuration Commands

```bash
# View configuration
relic --config --list              # List all config values

# Set values
relic --config core.server https://api.relic.example.com
relic --config core.timeout 60
relic --config client.key abc123
relic --config defaults.access_level public
relic --config defaults.expires_in 24h

# Get single value
relic --config core.server         # Print server URL

# Initialize config
relic --init                       # Create ~/.relic/config with defaults
```

### Environment Variables

All config values can be overridden via environment variables:

```bash
export RELIC_SERVER=https://api.relic.example.com
export RELIC_CLIENT_KEY=abc123
export RELIC_TIMEOUT=30
export RELIC_ACCESS_LEVEL=private
export RELIC_EXPIRES_IN=never
export RELIC_PROGRESS=true
```

## Implementation Details

### Configuration Priority (highest to lowest)

1. Command-line flags (--access-level, --expires-in, etc.)
2. Environment variables (RELIC_*)
3. Config file (~/.relic/config)
4. Built-in defaults

### Content Type Detection Strategy

```go
// Priority order:
1. File extension mapping (if filename provided)
2. Content sniffing (first 512 bytes via http.DetectContentType)
3. Fallback to text/plain
```

### Language Hint Detection

```go
// For syntax highlighting:
1. User-specified --language flag
2. File extension mapping (.py → python, .js → javascript, etc.)
3. Content-based detection (shebang line for scripts)
4. Leave empty if uncertain
```

### stdin vs File Detection

```go
import "os"

func isStdin() bool {
    stat, _ := os.Stdin.Stat()
    return (stat.Mode() & os.ModeCharDevice) == 0
}

// Usage:
// relic                → error if TTY, read if pipe
// relic -              → explicit stdin
// relic file.txt       → file upload
// echo "x" | relic     → stdin detected
```

### Progress Bar Behavior

- Show progress bar by default for file uploads
- Show progress bar for stdin if size can be determined
- Hide progress bar if --quiet or --output json/url
- Hide progress bar if output is not a TTY
- Update every 100ms or 1% progress, whichever is less frequent

### Error Recovery

**Network Errors**:
```go
// Retry strategy:
maxRetries := 3
backoff := []time.Duration{1 * time.Second, 2 * time.Second, 4 * time.Second}

for attempt := 0; attempt < maxRetries; attempt++ {
    err := uploadRelic(...)
    if err == nil {
        return nil
    }
    if !isRetryable(err) {
        return err
    }
    time.Sleep(backoff[attempt])
}
```

**File I/O Errors**:
- Check file exists before upload
- Check file size against 100MB limit
- Check read permissions
- Stream file (don't load into memory)

**Authentication Errors**:
- Generate client key automatically on first use
- Save to config file
- Prompt user to verify client key if 401/403

### Output Formatting

**Human-readable** (default):
```
✓ Created relic: a3Bk9Zx
  URL: https://relic.example.com/a3Bk9Zx
  Name: script.py
  Size: 2.1 KB
  Type: text/x-python
  Access: private
```

**JSON** (--output json):
```json
{
  "id": "a3Bk9Zx",
  "url": "https://relic.example.com/a3Bk9Zx",
  "name": "script.py",
  "size_bytes": 2150,
  "content_type": "text/x-python",
  "access_level": "private",
  "created_at": "2024-01-15T14:23:10Z"
}
```

**URL-only** (--output url or --quiet):
```
https://relic.example.com/a3Bk9Zx
```

## Testing Strategy

### Unit Tests
- Configuration loading and precedence
- MIME type detection
- stdin detection
- Output formatting
- Error handling

### Integration Tests
- End-to-end upload workflow
- Fork operations
- Delete operations
- Authentication flow
- Config file management

### Manual Testing Checklist
- [ ] Upload file
- [ ] Upload from stdin (pipe)
- [ ] Upload with password
- [ ] Upload with expiration
- [ ] List relics
- [ ] Get relic info
- [ ] Download relic
- [ ] Fork relic
- [ ] Delete relic
- [ ] Client key generation
- [ ] Config file creation
- [ ] Environment variable override
- [ ] Progress bar display
- [ ] Error messages
- [ ] Retry on network failure

## Distribution & Installation

### Build Process

```bash
# Makefile targets
make build          # Build for current platform
make build-all      # Build for all platforms (Linux, macOS, Windows)
make install        # Install to /usr/local/bin
make clean          # Clean build artifacts
make test           # Run tests
make lint           # Run linters
```

### Release Binaries

Build for multiple platforms:
```bash
GOOS=linux GOARCH=amd64 go build -o bin/relic-linux-amd64 cmd/relic/main.go
GOOS=darwin GOARCH=amd64 go build -o bin/relic-darwin-amd64 cmd/relic/main.go
GOOS=darwin GOARCH=arm64 go build -o bin/relic-darwin-arm64 cmd/relic/main.go
GOOS=windows GOARCH=amd64 go build -o bin/relic-windows-amd64.exe cmd/relic/main.go
```

### Installation Methods

**Manual**:
```bash
# Download binary
curl -LO https://github.com/example/relic-cli/releases/latest/download/relic-linux-amd64

# Make executable and move to PATH
chmod +x relic-linux-amd64
sudo mv relic-linux-amd64 /usr/local/bin/relic
```

**From source**:
```bash
git clone https://github.com/example/relic-cli
cd relic-cli/cli/client
make build
sudo make install
```

**Package managers** (future):
- Homebrew (macOS/Linux): `brew install relic`
- APT (Debian/Ubuntu): `apt install relic`
- Snap (Linux): `snap install relic`
- Chocolatey (Windows): `choco install relic`

## Implementation Phases

### Phase 1: Core Functionality (MVP)
- [x] Basic file upload
- [x] stdin support
- [x] Configuration management
- [x] Client key generation
- [x] Progress bars
- [x] Output formatting (human, JSON, URL)

### Phase 2: Advanced Features
- [ ] List relics
- [ ] Get relic info
- [ ] Download relics
- [ ] Fork operations
- [ ] Delete operations
- [ ] Password protection

### Phase 3: Polish & Distribution
- [ ] Comprehensive error messages
- [ ] Retry logic
- [ ] Colored output
- [ ] Interactive prompts
- [ ] Build pipeline
- [ ] Release binaries

### Phase 4: Future Enhancements
- [ ] Search functionality (when backend supports it)
- [ ] Tag management
- [ ] Bulk operations
- [ ] Config profiles (multiple servers)
- [ ] Shell completions (bash, zsh, fish)
- [ ] Update notifications

## Security Considerations

1. **Client key storage**: Plain text in config file (chmod 600)
2. **Password handling**: Never log passwords, use secure prompts
3. **HTTPS only**: Warn if server URL is HTTP
4. **File validation**: Check file size before upload
5. **Input sanitization**: Validate user input for injection risks
6. **Temporary files**: Clean up on exit or error
7. **Config file permissions**: Create with 600 (owner read/write only)

## Performance Goals

- Upload startup latency: < 100ms (excluding network)
- Progress update frequency: Every 100ms or 1% progress
- Memory usage: < 50MB for CLI overhead (streaming, not buffering files)
- Binary size: < 10MB (static binary with all dependencies)
- Config load time: < 10ms

## Accessibility & Usability

- **Color blindness**: Use symbols (✓, ✗, ⚠) in addition to colors
- **Screen readers**: Plain text mode available via --no-color
- **Terminal compatibility**: Test on various terminals (xterm, iTerm, Windows Terminal)
- **Documentation**: Comprehensive help text with examples
- **Error messages**: Clear, actionable error messages with suggestions

## Future Considerations

### Desktop Integration
- Drag-and-drop support (via desktop app wrapper)
- System tray integration
- File association (open .relic files)

### Advanced CLI Features
- Interactive TUI mode (like `tig` for git)
- Relic browser/viewer in terminal
- Diff viewer for forks
- Watch mode (auto-upload on file change)

### API Coverage
- Implement all Relic API endpoints
- GraphQL support (if backend adds it)
- Webhook notifications
- Real-time updates

---

## Appendix: Examples

### Example 1: Quick Paste
```bash
echo "Quick note" | relic
# ✓ Created relic: https://relic.example.com/a3Bk9Zx
```

### Example 2: Upload Script with Metadata
```bash
relic deploy.sh \
  --name "Production Deploy Script" \
  --description "Automated deployment to production" \
  --access-level private \
  --expires-in 30d
```

### Example 3: Pipe Command Output
```bash
ps aux | relic --name "process-list-$(date +%Y%m%d).txt"
```

### Example 4: Download and Process
```bash
# Download relic and process with jq
relic --get a3Bk9Zx | jq '.results[] | .name'
```

### Example 5: Fork and Modify
```bash
# Download, modify, and create fork
relic --get x7Yz8Wx -o temp.txt
sed -i 's/old/new/g' temp.txt
cat temp.txt | relic --name "modified-version.txt"
rm temp.txt
```

### Example 6: Batch Upload
```bash
# Upload all Python files
find . -name "*.py" -type f | while read file; do
  echo "Uploading $file"
  relic "$file" --output url >> uploaded-urls.txt
done
```

### Example 7: JSON Output for Scripting
```bash
# Create relic and extract ID for later use
ID=$(relic script.sh --output json | jq -r '.id')
echo "Created relic with ID: $ID"

# Later, delete it
relic --delete "$ID" --yes
```