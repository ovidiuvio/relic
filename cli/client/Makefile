# Makefile for Relic CLI

.PHONY: build build-all install clean test lint help

# Binary name
BINARY_NAME=relic
VERSION?=0.1.0
BUILD_DIR=bin

# Go build flags
# CGO_ENABLED=0 creates fully static binaries compatible with older glibc (RHEL 8, etc.)
# -trimpath removes absolute paths for reproducible builds
# -s -w strips debug info to reduce binary size
LDFLAGS=-ldflags "-s -w -X main.Version=$(VERSION)"
BUILDFLAGS=CGO_ENABLED=0

# Default target
all: build

## build: Build binary for current platform
build:
	@echo "Building $(BINARY_NAME)..."
	@mkdir -p $(BUILD_DIR)
	$(BUILDFLAGS) go build -trimpath $(LDFLAGS) -o $(BUILD_DIR)/$(BINARY_NAME) cmd/relic/main.go
	@echo "✓ Built $(BUILD_DIR)/$(BINARY_NAME)"

## build-all: Build binaries for all platforms
build-all:
	@echo "Building for all platforms..."
	@mkdir -p $(BUILD_DIR)
	$(BUILDFLAGS) GOOS=linux GOARCH=amd64 go build -trimpath $(LDFLAGS) -o $(BUILD_DIR)/$(BINARY_NAME)-linux-amd64 cmd/relic/main.go
	$(BUILDFLAGS) GOOS=linux GOARCH=arm64 go build -trimpath $(LDFLAGS) -o $(BUILD_DIR)/$(BINARY_NAME)-linux-arm64 cmd/relic/main.go
	$(BUILDFLAGS) GOOS=darwin GOARCH=amd64 go build -trimpath $(LDFLAGS) -o $(BUILD_DIR)/$(BINARY_NAME)-darwin-amd64 cmd/relic/main.go
	$(BUILDFLAGS) GOOS=darwin GOARCH=arm64 go build -trimpath $(LDFLAGS) -o $(BUILD_DIR)/$(BINARY_NAME)-darwin-arm64 cmd/relic/main.go
	$(BUILDFLAGS) GOOS=windows GOARCH=amd64 go build -trimpath $(LDFLAGS) -o $(BUILD_DIR)/$(BINARY_NAME)-windows-amd64.exe cmd/relic/main.go
	@echo "✓ Built all platform binaries in $(BUILD_DIR)/"

## install: Install binary to /usr/local/bin
install: build
	@echo "Installing $(BINARY_NAME) to /usr/local/bin..."
	sudo cp $(BUILD_DIR)/$(BINARY_NAME) /usr/local/bin/$(BINARY_NAME)
	@echo "✓ Installed $(BINARY_NAME)"

## clean: Remove build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf $(BUILD_DIR)
	go clean
	@echo "✓ Cleaned"

## test: Run tests
test:
	@echo "Running tests..."
	go test -v ./...
	@echo "✓ Tests passed"

## lint: Run linters
lint:
	@echo "Running linters..."
	@which golangci-lint > /dev/null || (echo "golangci-lint not installed. Install with: go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest" && exit 1)
	golangci-lint run
	@echo "✓ Linting passed"

## deps: Download dependencies
deps:
	@echo "Downloading dependencies..."
	go mod download
	go mod tidy
	@echo "✓ Dependencies updated"

## run: Run the CLI (development)
run:
	go run cmd/relic/main.go $(ARGS)

## help: Show this help message
help:
	@echo "Relic CLI - Makefile commands:"
	@echo ""
	@sed -n 's/^##//p' ${MAKEFILE_LIST} | column -t -s ':' | sed -e 's/^/ /'
