# Relic CLI - Quick Start Guide

Get started with the Relic CLI in 5 minutes!

## 1. Build the CLI

```bash
cd cli/client
make build
```

This creates the binary at `bin/relic`.

## 2. Test It Works

```bash
./bin/relic --version
# relic version 0.1.0

./bin/relic --help
# Shows help text
```

## 3. Start the Relic Backend

Make sure the Relic backend server is running:

```bash
# In the project root directory
cd backend
uvicorn backend.main:app --reload
```

The server should be running at `http://localhost:8000`.

## 4. Initialize Configuration (Optional)

```bash
./bin/relic init
```

This creates `~/.relic/config` with default settings.

## 5. Upload Your First Relic

### From a File

```bash
./bin/relic README.md
```

You'll see:
```
ℹ Generated new client key: f47ac10b...
✓ Client key saved to config
Uploading: 100% |████████████████████| 2.1 KB/2.1 KB
✓ Created relic: a3Bk9Zx
  URL: http://localhost:8000/a3Bk9Zx
  Name: README.md
  Size: 2.1 KB
  Type: text/markdown
  Access: private
```

### From Stdin

```bash
echo "Hello, Relic!" | ./bin/relic --name "greeting.txt"
```

### From Command Output

```bash
git log | ./bin/relic --name "git-history.txt"
ps aux | ./bin/relic --name "processes.txt"
```

## 6. View Your Relics

```bash
./bin/relic list
```

Output:
```
ID          Name            Size    Type        Created    Access
a3Bk9Zx     README.md       2.1KB   Markdown    2m ago     private
x7Yz8Wx     greeting.txt    15B     Plain       1m ago     private

Total: 2 relics
```

## 7. Get Relic Info

```bash
./bin/relic info a3Bk9Zx
```

Output:
```
Relic: a3Bk9Zx
Name: README.md
Size: 2.1 KB
Type: text/markdown (markdown)
Created: 2024-01-15 14:23:10 UTC
Access: private
Views: 1
```

## 8. Download a Relic

```bash
# To stdout
./bin/relic get a3Bk9Zx

# To file
./bin/relic get a3Bk9Zx -o downloaded.md
```

## 9. Fork a Relic

```bash
./bin/relic fork a3Bk9Zx --name "Modified README"
```

## 10. Delete a Relic

```bash
./bin/relic delete x7Yz8Wx
# Confirm: Delete relic x7Yz8Wx? [y/N]: y
# ✓ Deleted relic: x7Yz8Wx

# Or skip confirmation
./bin/relic delete x7Yz8Wx --yes
```

## Common Use Cases

### Share Command Output

```bash
# Capture and share system info
uname -a | ./bin/relic --name "system-info.txt" -q
# http://localhost:8000/a3Bk9Zx

# Share that URL with others!
```

### Quick Notes

```bash
echo "Remember to buy milk" | ./bin/relic --name "note.txt"
```

### Code Snippets

```bash
./bin/relic snippet.py \
  --description "Python script for data processing" \
  --access-level public \
  --expires-in 7d
```

### Backup Files

```bash
tar -czf - ./important-data | ./bin/relic --name "backup-$(date +%Y%m%d).tar.gz"
```

### JSON Output for Scripting

```bash
# Create relic and extract ID
ID=$(./bin/relic script.sh --output json | jq -r '.id')

# Use ID for something else
echo "Created relic with ID: $ID"
./bin/relic info "$ID"
```

### Batch Upload

```bash
# Upload all Python files
for file in *.py; do
    ./bin/relic "$file" --output url >> uploaded-urls.txt
done
```

## Configuration

### View Current Configuration

```bash
./bin/relic config --list
```

### Change Server URL

```bash
./bin/relic config core.server https://api.relic.example.com
```

### Use Environment Variables

```bash
export RELIC_SERVER=http://localhost:8000
export RELIC_ACCESS_LEVEL=public
export RELIC_EXPIRES_IN=7d

./bin/relic file.txt  # Uses environment variables
```

### Command-line Overrides

```bash
./bin/relic file.txt \
  --server http://different-server.com \
  --access-level public \
  --expires-in 24h
```

## Output Formats

### Human (Default)

```bash
./bin/relic script.py
```

Colored, formatted output with symbols.

### JSON (for scripts)

```bash
./bin/relic script.py --output json
```

Machine-readable JSON.

### URL Only (for sharing)

```bash
./bin/relic script.py --output url
# or
./bin/relic script.py -q
```

Just the URL for easy copying/sharing.

## Tips & Tricks

### Install Globally (Optional)

```bash
sudo make install
```

Now you can use `relic` instead of `./bin/relic`:

```bash
relic file.txt
```

### Quiet Mode for Scripting

```bash
URL=$(echo "test" | relic -q)
echo "Relic URL: $URL"
```

### Verbose Mode for Debugging

```bash
./bin/relic file.txt --verbose
```

Shows HTTP requests/responses.

### Disable Progress Bar

```bash
./bin/relic large-file.zip --no-progress
```

### Check Your Client Info

```bash
./bin/relic whoami
```

Output:
```
Client ID: f47ac10b58cc4372a5670e02b2c3d479
Server: http://localhost:8000
Registered: 2024-01-15 14:20:00 UTC
Relics: 5
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [DESIGN.md](DESIGN.md) for architectural details
- View [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for implementation details

## Troubleshooting

### "Connection failed"

Make sure the backend server is running:
```bash
cd backend
uvicorn backend.main:app --reload
```

### "File too large"

Maximum file size is 100MB. Compress large files:
```bash
tar -czf - large-dir | relic --name "archive.tar.gz"
```

### Want to use a different server?

```bash
export RELIC_SERVER=https://your-server.com
# or
./bin/relic config core.server https://your-server.com
```

## Have Fun!

The Relic CLI makes it easy to store and share anything from your terminal. Try piping different commands and see what you can create!

```bash
# Share your Git history
git log --oneline | relic --name "git-log.txt" -q

# Share network info
ifconfig | relic --name "network.txt" -q

# Share directory listing
ls -la | relic --name "directory.txt" -q

# Share your environment
env | relic --name "env-vars.txt" --access-level private -q
```
