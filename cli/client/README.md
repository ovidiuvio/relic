# Relic CLI

A command-line interface for the Relic artifact storage service. Upload, manage, and share immutable artifacts from your terminal.

## Features

- **Simple uploads**: Pipe content or upload files with a single command
- **Immutable storage**: All relics are permanent and cannot be edited
- **Fork workflow**: Create independent copies of relics for modifications
- **Multiple output formats**: Human-readable, JSON, or URL-only output
- **Progress tracking**: Visual progress bars for uploads
- **Flexible configuration**: Config file, environment variables, and command-line flags
- **Cross-platform**: Works on Linux, macOS, and Windows

## Installation

### From Source

```bash
cd cli/client
make build
sudo make install
```

### Download Binary

Download the latest release for your platform from the releases page, then:

```bash
chmod +x relic-linux-amd64
sudo mv relic-linux-amd64 /usr/local/bin/relic
```

## Quick Start

### Upload a File

```bash
relic script.py
```

### Upload from Stdin

```bash
echo "Hello, World!" | relic
```

### Upload with Options

```bash
relic deploy.sh \
  --name "Production Deploy Script" \
  --description "Automated deployment script" \
  --access-level private \
  --expires-in 30d
```

### List Your Relics

```bash
relic list
```

### Get Relic Info

```bash
relic info a3Bk9Zx
```

### Download a Relic

```bash
relic get a3Bk9Zx -o output.txt
```

### Fork a Relic

```bash
relic fork a3Bk9Zx --name "My Modified Version"
```

## Usage

### Upload Command (Default)

```bash
relic [FILE]
```

Upload a file or read from stdin. If no file is specified and stdin is a pipe, reads from stdin.

**Flags:**
- `-n, --name NAME` - Set relic name (default: filename or "stdin")
- `-d, --description DESC` - Set description
- `-l, --language LANG` - Set language hint for syntax highlighting
- `-a, --access-level LEVEL` - Set access level: `public` or `private` (default: private)
- `-e, --expires-in DURATION` - Set expiration: `1h`, `24h`, `7d`, `30d`, `never` (default: never)
- `-p, --password PASSWORD` - Set password protection
- `--no-progress` - Disable progress bar

**Examples:**

```bash
# Upload file with auto-detection
relic script.py

# Upload from pipe
cat data.json | relic --name "api-response.json"

# Upload with metadata
relic README.md \
  --description "Project documentation" \
  --access-level public \
  --expires-in 7d

# Upload with password
relic secret.txt --password mypassword
```

### Info Command

```bash
relic info ID
```

Get detailed information about a relic.

**Examples:**

```bash
# Human-readable output
relic info a3Bk9Zx

# JSON output
relic info a3Bk9Zx --output json
```

### List Command

```bash
relic list
```

List your relics (requires client key).

**Flags:**
- `--limit N` - Limit results (default: 20)
- `--offset N` - Pagination offset
- `--access-level LEVEL` - Filter by access level

**Examples:**

```bash
# List recent relics
relic list

# List private relics only
relic list --access-level private

# Paginate results
relic list --limit 50 --offset 100
```

### Recent Command

```bash
relic recent
```

List recent public relics from all users.

**Flags:**
- `--limit N` - Limit results (default: 20)
- `--offset N` - Pagination offset

### Get Command

```bash
relic get ID
```

Download relic content to stdout or a file.

**Flags:**
- `-o, --output FILE` - Save to file instead of stdout

**Examples:**

```bash
# Download to stdout
relic get a3Bk9Zx

# Save to file
relic get a3Bk9Zx -o script.py

# Pipe to another command
relic get a3Bk9Zx | jq '.results'
```

### Fork Command

```bash
relic fork ID
```

Create an independent copy of a relic.

**Flags:**
- `-n, --name NAME` - New relic name
- `-d, --description DESC` - New description
- `-a, --access-level LEVEL` - Access level for fork

**Examples:**

```bash
# Simple fork
relic fork a3Bk9Zx

# Fork with new metadata
relic fork a3Bk9Zx \
  --name "Modified Script" \
  --description "Customized version" \
  --access-level private
```

### Delete Command

```bash
relic delete ID
```

Delete a relic (soft delete). Only the owner can delete their relics.

**Flags:**
- `-y, --yes` - Skip confirmation prompt

**Examples:**

```bash
# Delete with confirmation
relic delete a3Bk9Zx

# Delete without confirmation
relic delete a3Bk9Zx --yes
```

### Whoami Command

```bash
relic whoami
```

Show current client information including client ID, server URL, and relic count.

### Config Command

```bash
relic config [key] [value]
```

Manage configuration values.

**Flags:**
- `--list` - List all config values

**Examples:**

```bash
# List all config
relic config --list

# Get single value
relic config core.server

# Set value
relic config core.server https://api.relic.example.com
relic config defaults.access_level public
relic config client.key abc123def456
```

### Init Command

```bash
relic init
```

Create a default configuration file at `~/.relic/config`.

## Configuration

Configuration priority (highest to lowest):

1. Command-line flags
2. Environment variables (with `RELIC_` prefix)
3. Config file (`~/.relic/config`)
4. Built-in defaults

### Config File

Location: `~/.relic/config`

Format (INI-style):

```ini
[core]
    server = http://localhost:8000
    timeout = 30
    progress = true

[client]
    key = f47ac10b58cc4372a5670e02b2c3d479

[defaults]
    access_level = private
    expires_in = never
```

### Environment Variables

```bash
export RELIC_SERVER=http://localhost:8000
export RELIC_CLIENT_KEY=abc123
export RELIC_TIMEOUT=30
export RELIC_ACCESS_LEVEL=private
export RELIC_EXPIRES_IN=never
export RELIC_PROGRESS=true
```

## Global Flags

These flags work with all commands:

- `-v, --verbose` - Verbose output (show HTTP requests/responses)
- `-o, --output FORMAT` - Output format: `human`, `json`, `url` (default: human)
- `-q, --quiet` - Quiet mode (URL only for create/fork, minimal output for other commands)
- `--server URL` - Override API server URL
- `--client-key KEY` - Override client key

## Output Formats

### Human (Default)

Colored, formatted output optimized for terminal viewing.

```bash
relic script.py
# ✓ Created relic: a3Bk9Zx
#   URL: http://localhost:8000/a3Bk9Zx
#   Name: script.py
#   Size: 2.1 KB
#   Type: text/x-python
#   Access: private
```

### JSON

Machine-readable JSON output for scripting.

```bash
relic script.py --output json
# {
#   "id": "a3Bk9Zx",
#   "url": "http://localhost:8000/a3Bk9Zx",
#   "name": "script.py",
#   ...
# }
```

### URL

URL-only output for easy piping and scripting.

```bash
relic script.py --output url
# http://localhost:8000/a3Bk9Zx
```

Or use `--quiet` / `-q`:

```bash
relic script.py -q
# http://localhost:8000/a3Bk9Zx
```

## Examples

### Quick Paste

```bash
echo "Quick note" | relic
```

### Pipe Command Output

```bash
ps aux | relic --name "processes.txt"
git log | relic --name "commit-history.txt"
```

### Download and Process

```bash
# Download and parse JSON
relic get a3Bk9Zx | jq '.results[] | .name'

# Download and edit
relic get x7Yz8Wx -o temp.txt
vim temp.txt
cat temp.txt | relic --name "edited-version.txt"
```

### Batch Upload

```bash
# Upload all Python files
find . -name "*.py" -type f | while read file; do
  echo "Uploading $file"
  relic "$file" --output url >> urls.txt
done
```

### Fork and Modify Workflow

```bash
# Download original
relic get x7Yz8Wx -o script.sh

# Modify
sed -i 's/old/new/g' script.sh

# Upload as new relic (fork manually)
cat script.sh | relic --name "modified-script.sh"
```

### Scripting with JSON

```bash
# Create relic and extract ID
ID=$(relic script.sh --output json | jq -r '.id')
echo "Created relic with ID: $ID"

# Get info as JSON
relic info "$ID" --output json | jq '.size_bytes'

# Delete
relic delete "$ID" --yes
```

## Client Key Management

On first use, the CLI automatically generates a random client key and saves it to your config file. This key identifies you to the server and allows you to:

- List your relics
- Delete your relics
- View your relic count

**View your client info:**

```bash
relic whoami
```

**Manually set a client key:**

```bash
relic config client.key YOUR_KEY_HERE
# or
export RELIC_CLIENT_KEY=YOUR_KEY_HERE
```

## Access Levels

- **Private** (default): Not listed in public recent relics, only accessible via direct URL (URL serves as access token)
- **Public**: Listed in recent public relics, discoverable by anyone

Both levels allow direct access via URL. Private relics simply aren't listed publicly.

## Expiration

Set an expiration time for automatic cleanup:

- `1h` - 1 hour
- `24h` - 24 hours
- `7d` - 7 days
- `30d` - 30 days
- `never` - No expiration (default)

Expired relics are soft-deleted after the expiration time.

## Password Protection

Add password protection to any relic:

```bash
relic secret.txt --password mypassword
```

Users will need to provide the password when accessing the relic via the web interface.

## Development

### Build

```bash
make build
```

### Build for All Platforms

```bash
make build-all
```

### Run Tests

```bash
make test
```

### Clean

```bash
make clean
```

## Troubleshooting

### "No client key found"

Generate a client key by creating a relic:

```bash
echo "test" | relic
```

Or initialize config:

```bash
relic init
```

### "Connection failed"

Check server URL:

```bash
relic config core.server
```

Set correct server:

```bash
relic config core.server http://localhost:8000
```

Or use environment variable:

```bash
export RELIC_SERVER=http://localhost:8000
```

### "File too large"

Maximum file size is 100MB. Split larger files or use compression:

```bash
tar -czf - large-directory | relic --name "archive.tar.gz"
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions welcome! Please open an issue or pull request.

## Support

For bugs and feature requests, please open an issue on GitHub.
