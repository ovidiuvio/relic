#!/bin/bash
set -e

# Relic CLI Installation Script
# Usage: curl -sSL https://your-relic-server/install.sh | bash

VERSION="${RELIC_VERSION:-latest}"
INSTALL_DIR="${RELIC_INSTALL_DIR:-/usr/local/bin}"
CONFIG_DIR="$HOME/.relic"
BINARY_NAME="relic"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Detect platform
detect_platform() {
    local os=""
    local arch=""

    # Detect OS
    case "$(uname -s)" in
        Linux*)     os="linux";;
        Darwin*)    os="darwin";;
        MINGW*|MSYS*|CYGWIN*)    os="windows";;
        *)
            echo -e "${RED}Error: Unsupported operating system$(uname -s)${NC}"
            exit 1
            ;;
    esac

    # Detect architecture
    case "$(uname -m)" in
        x86_64|amd64)   arch="amd64";;
        aarch64|arm64)  arch="arm64";;
        *)
            echo -e "${RED}Error: Unsupported architecture $(uname -m)${NC}"
            exit 1
            ;;
    esac

    echo "${os}-${arch}"
}

# Get download URL from GitHub releases
get_download_url() {
    local platform=$1
    local repo="${RELIC_REPO:-ovidiuvio/relic}"  # Update with your GitHub repo

    # Construct binary name
    local binary_name="relic-${platform}"
    if [[ "$platform" == "windows-"* ]]; then
        binary_name="${binary_name}.exe"
    fi

    if [ "$VERSION" = "latest" ]; then
        echo "https://github.com/${repo}/releases/latest/download/${binary_name}"
    else
        echo "https://github.com/${repo}/releases/download/v${VERSION}/${binary_name}"
    fi
}

# Download and install binary
install_binary() {
    local platform=$1
    local url=$(get_download_url "$platform")
    local temp_file="/tmp/${BINARY_NAME}-$$"

    echo -e "${YELLOW}Downloading Relic CLI from ${url}...${NC}"

    if command -v curl > /dev/null 2>&1; then
        curl -fsSL "$url" -o "$temp_file"
    elif command -v wget > /dev/null 2>&1; then
        wget -q "$url" -O "$temp_file"
    else
        echo -e "${RED}Error: curl or wget is required${NC}"
        exit 1
    fi

    # Make executable
    chmod +x "$temp_file"

    # Install to target directory
    if [ -w "$INSTALL_DIR" ]; then
        mv "$temp_file" "$INSTALL_DIR/$BINARY_NAME"
    else
        echo -e "${YELLOW}Installing to $INSTALL_DIR (requires sudo)...${NC}"
        sudo mv "$temp_file" "$INSTALL_DIR/$BINARY_NAME"
    fi

    echo -e "${GREEN}✓ Installed $BINARY_NAME to $INSTALL_DIR/$BINARY_NAME${NC}"
}

# Create initial config
create_config() {
    if [ ! -d "$CONFIG_DIR" ]; then
        mkdir -p "$CONFIG_DIR"
        echo -e "${GREEN}✓ Created config directory: $CONFIG_DIR${NC}"
    fi

    if [ ! -f "$CONFIG_DIR/config" ]; then
        local server="${RELIC_SERVER:-http://localhost}"
        cat > "$CONFIG_DIR/config" <<EOF
[core]
    server = $server
    timeout = 30
    progress = true

[defaults]
    access_level = private
    expires_in = never
EOF
        echo -e "${GREEN}✓ Created default config: $CONFIG_DIR/config${NC}"
    else
        echo -e "${YELLOW}Config already exists: $CONFIG_DIR/config${NC}"
    fi
}

# Main installation
main() {
    echo ""
    echo "=================================="
    echo "  Relic CLI Installation"
    echo "=================================="
    echo ""

    # Detect platform
    local platform=$(detect_platform)
    echo -e "Detected platform: ${GREEN}${platform}${NC}"
    echo ""

    # Install binary
    install_binary "$platform"
    echo ""

    # Create config
    create_config
    echo ""

    # Verify installation
    if command -v "$BINARY_NAME" > /dev/null 2>&1; then
        local version=$("$BINARY_NAME" --version 2>&1 || echo "unknown")
        echo -e "${GREEN}✓ Installation successful!${NC}"
        echo ""
        echo "Version: $version"
        echo ""
        echo "Quick Start:"
        echo "  echo 'Hello World' | relic              # Upload from stdin"
        echo "  relic file.txt                          # Upload a file"
        echo "  relic list                              # List your relics"
        echo "  relic --help                            # Show all commands"
        echo ""
        echo "Configuration: $CONFIG_DIR/config"
        echo ""
    else
        echo -e "${YELLOW}⚠ Installation completed but $BINARY_NAME not found in PATH${NC}"
        echo "You may need to add $INSTALL_DIR to your PATH"
        echo "Or run: export PATH=\"\$PATH:$INSTALL_DIR\""
    fi
}

main
