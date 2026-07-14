package cli_test

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

var relicBinaryPath string
var testServerURL string

func TestMain(m *testing.M) {
	// Determine server URL
	testServerURL = os.Getenv("TEST_RELIC_SERVER")
	if testServerURL == "" {
		testServerURL = "http://localhost"
	}

	// Compile relic binary
	tempDir, err := os.MkdirTemp("", "relic-cli-test")
	if err != nil {
		log.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	relicBinaryPath = filepath.Join(tempDir, "relic")

	// Compile binary
	cmd := exec.Command("go", "build", "-o", relicBinaryPath, "cmd/relic/main.go")
	if err := cmd.Run(); err != nil {
		log.Fatalf("Failed to build relic binary: %v", err)
	}

	os.Exit(m.Run())
}

// setupTestEnv creates a temporary home directory and base environment map
func setupTestEnv(t *testing.T) (string, map[string]string) {
	t.Helper()

	tempHome, err := os.MkdirTemp("", "relic-home-*")
	if err != nil {
		t.Fatalf("Failed to create temp home directory: %v", err)
	}

	t.Cleanup(func() {
		os.RemoveAll(tempHome)
	})

	env := map[string]string{
		"HOME": tempHome,
	}

	return tempHome, env
}

// runCLI executes the compiled relic CLI with environment and arguments
func runCLI(t *testing.T, env map[string]string, args ...string) (string, string, error, int) {
	t.Helper()
	return runCLIWithStdin(t, nil, env, args...)
}

// runCLIWithStdin executes the compiled relic CLI with stdin, environment, and arguments
func runCLIWithStdin(t *testing.T, stdin io.Reader, env map[string]string, args ...string) (string, string, error, int) {
	t.Helper()

	cmd := exec.Command(relicBinaryPath, args...)

	// Setup environment
	cmd.Env = os.Environ()
	for k, v := range env {
		cmd.Env = append(cmd.Env, fmt.Sprintf("%s=%s", k, v))
	}

	if stdin != nil {
		cmd.Stdin = stdin
	}

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err := cmd.Run()

	exitCode := 0
	if err != nil {
		if exitError, ok := err.(*exec.ExitError); ok {
			exitCode = exitError.ExitCode()
		} else {
			exitCode = -1
		}
	}

	return stdout.String(), stderr.String(), err, exitCode
}

// checkServer checks if the server is available, otherwise skips the test
func checkServer(t *testing.T) {
	t.Helper()
	client := &http.Client{Timeout: 2 * time.Second}
	resp, err := client.Get(testServerURL + "/health")
	if err != nil {
		t.Skipf("Relic server not running at %s, skipping integration test: %v", testServerURL, err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Skipf("Relic server returned status %d, skipping integration test", resp.StatusCode)
	}
}

func TestCLI_InitAndConfig(t *testing.T) {
	_, env := setupTestEnv(t)

	// 1. Run relic init
	stdout, stderr, err, exitCode := runCLI(t, env, "init")
	if err != nil {
		t.Fatalf("relic init failed: %v, stderr: %s", err, stderr)
	}
	if exitCode != 0 {
		t.Fatalf("expected exit code 0, got %d", exitCode)
	}
	if !strings.Contains(stdout, "Created config file") {
		t.Errorf("unexpected output from relic init: %s", stdout)
	}

	// Verify file was created
	configPath := filepath.Join(env["HOME"], ".relic", "config")
	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		t.Fatalf("config file was not created at %s", configPath)
	}

	// 2. Read config value
	stdout, stderr, err, exitCode = runCLI(t, env, "config", "core.server")
	if err != nil {
		t.Fatalf("relic config get failed: %v, stderr: %s", err, stderr)
	}
	if strings.TrimSpace(stdout) != "http://localhost:8000" { // Default loaded from config
		t.Errorf("expected default server http://localhost:8000, got %q", stdout)
	}

	// 3. Set config value
	stdout, stderr, err, exitCode = runCLI(t, env, "config", "core.server", "http://test-server:9000")
	if err != nil {
		t.Fatalf("relic config set failed: %v, stderr: %s", err, stderr)
	}
	if !strings.Contains(stdout, "Set core.server = http://test-server:9000") {
		t.Errorf("unexpected set output: %s", stdout)
	}

	// 4. Verify set value
	stdout, _, _, _ = runCLI(t, env, "config", "core.server")
	if strings.TrimSpace(stdout) != "http://test-server:9000" {
		t.Errorf("expected http://test-server:9000, got %q", stdout)
	}

	// 5. List config
	stdout, _, _, _ = runCLI(t, env, "config", "--list")
	if !strings.Contains(stdout, "core.server = http://test-server:9000") {
		t.Errorf("expected list to show server, got: %s", stdout)
	}
}

func TestCLI_Whoami(t *testing.T) {
	checkServer(t)
	_, env := setupTestEnv(t)
	env["RELIC_SERVER"] = testServerURL

	// Running whoami without a client key should fail
	_, stderr, _, exitCode := runCLI(t, env, "whoami")
	if exitCode == 0 {
		t.Error("expected whoami to fail without client key")
	}
	if !strings.Contains(stderr, "No client key found") {
		t.Errorf("unexpected error message: %s", stderr)
	}

	// Run an upload to generate a key automatically
	stdin := strings.NewReader("test content")
	_, _, err, exitCode := runCLIWithStdin(t, stdin, env, "-")
	if err != nil {
		t.Fatalf("relic upload failed: %v", err)
	}

	// Now whoami should work
	stdout, stderr, err, exitCode := runCLI(t, env, "whoami")
	if err != nil {
		t.Fatalf("whoami failed: %v, stderr: %s", err, stderr)
	}
	if exitCode != 0 {
		t.Fatalf("expected exit code 0, got %d", exitCode)
	}
	if !strings.Contains(stdout, "Client ID:") {
		t.Errorf("unexpected whoami output: %s", stdout)
	}
}

type RelicJSONResponse struct {
	ID        string `json:"id"`
	URL       string `json:"url"`
	ForkOf    string `json:"fork_of"`
	SizeBytes int64  `json:"size_bytes"`
	Tags      []struct {
		Name string `json:"name"`
	} `json:"tags"`
}

func TestCLI_UploadAndDownload(t *testing.T) {
	checkServer(t)
	_, env := setupTestEnv(t)
	env["RELIC_SERVER"] = testServerURL

	// 1. Test Stdin upload with JSON output
	content := "Hello World from Stdin Test"
	stdin := strings.NewReader(content)
	stdout, stderr, err, exitCode := runCLIWithStdin(t, stdin, env, "-", "-o", "json", "--name", "stdin-test.txt", "--tag", "test-tag", "--tag", "go-cli")
	if err != nil {
		t.Fatalf("stdin upload failed: %v, stderr: %s", err, stderr)
	}
	if exitCode != 0 {
		t.Fatalf("expected exit code 0, got %d", exitCode)
	}

	var uploadResp RelicJSONResponse
	if err := json.Unmarshal([]byte(stdout), &uploadResp); err != nil {
		t.Fatalf("failed to parse JSON upload response: %v, stdout: %q", err, stdout)
	}

	if uploadResp.ID == "" {
		t.Fatal("uploaded relic ID is empty")
	}

	// 2. Test Get content to stdout
	stdout, stderr, err, exitCode = runCLI(t, env, "get", uploadResp.ID)
	if err != nil {
		t.Fatalf("relic get failed: %v, stderr: %s", err, stderr)
	}
	if stdout != content {
		t.Errorf("expected content %q, got %q", content, stdout)
	}

	// 3. Test Get metadata via info
	stdout, stderr, err, exitCode = runCLI(t, env, "info", uploadResp.ID, "-o", "json")
	if err != nil {
		t.Fatalf("relic info failed: %v, stderr: %s", err, stderr)
	}
	var infoResp RelicJSONResponse
	if err := json.Unmarshal([]byte(stdout), &infoResp); err != nil {
		t.Fatalf("failed to parse JSON info response: %v, stdout: %q", err, stdout)
	}

	if infoResp.SizeBytes != int64(len(content)) {
		t.Errorf("expected size %d, got %d", len(content), infoResp.SizeBytes)
	}

	hasTestTag := false
	hasGoCliTag := false
	for _, tag := range infoResp.Tags {
		if tag.Name == "test-tag" {
			hasTestTag = true
		}
		if tag.Name == "go-cli" {
			hasGoCliTag = true
		}
	}
	if !hasTestTag || !hasGoCliTag {
		t.Errorf("expected tags 'test-tag' and 'go-cli' to be present, got: %+v", infoResp.Tags)
	}

	// 4. Test File upload
	tempDir, err := os.MkdirTemp("", "relic-upload-test")
	if err != nil {
		t.Fatalf("failed to create temp upload dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	filePath := filepath.Join(tempDir, "file-test.txt")
	fileContent := "This is content from a test file."
	if err := os.WriteFile(filePath, []byte(fileContent), 0644); err != nil {
		t.Fatalf("failed to write temp file: %v", err)
	}

	stdout, stderr, err, exitCode = runCLI(t, env, filePath, "-o", "url")
	if err != nil {
		t.Fatalf("file upload failed: %v, stderr: %s", err, stderr)
	}
	fileRelicURL := strings.TrimSpace(stdout)
	if !strings.HasPrefix(fileRelicURL, testServerURL) {
		t.Errorf("expected URL output to start with %q, got %q", testServerURL, fileRelicURL)
	}

	// Get ID from URL
	parts := strings.Split(fileRelicURL, "/")
	fileRelicID := parts[len(parts)-1]

	// Download to file
	destPath := filepath.Join(tempDir, "downloaded.txt")
	stdout, stderr, err, exitCode = runCLI(t, env, "get", fileRelicID, "-o", destPath)
	if err != nil {
		t.Fatalf("get to file failed: %v, stderr: %s", err, stderr)
	}

	downloadedContent, err := os.ReadFile(destPath)
	if err != nil {
		t.Fatalf("failed to read downloaded file: %v", err)
	}

	if string(downloadedContent) != fileContent {
		t.Errorf("expected downloaded file content %q, got %q", fileContent, string(downloadedContent))
	}

	// 5. Test List
	stdout, stderr, err, exitCode = runCLI(t, env, "list", "-o", "json")
	if err != nil {
		t.Fatalf("list failed: %v, stderr: %s", err, stderr)
	}
	var listResp struct {
		Relics []RelicJSONResponse `json:"relics"`
	}
	if err := json.Unmarshal([]byte(stdout), &listResp); err != nil {
		t.Fatalf("failed to parse JSON list response: %v", err)
	}

	foundStdin := false
	foundFile := false
	for _, r := range listResp.Relics {
		if r.ID == uploadResp.ID {
			foundStdin = true
		}
		if r.ID == fileRelicID {
			foundFile = true
		}
	}
	if !foundStdin || !foundFile {
		t.Errorf("list did not return both uploaded relics (stdin: %t, file: %t)", foundStdin, foundFile)
	}

	// 6. Test Recent
	stdout, stderr, err, exitCode = runCLI(t, env, "recent", "-o", "json")
	if err != nil {
		t.Fatalf("recent failed: %v, stderr: %s", err, stderr)
	}

	// Clean up both relics
	_, _, err, _ = runCLI(t, env, "delete", uploadResp.ID, "--yes")
	if err != nil {
		t.Errorf("failed to delete stdin relic: %v", err)
	}
	_, _, err, _ = runCLI(t, env, "delete", fileRelicID, "--yes")
	if err != nil {
		t.Errorf("failed to delete file relic: %v", err)
	}
}

func TestCLI_ForkAndDelete(t *testing.T) {
	checkServer(t)
	_, env := setupTestEnv(t)
	env["RELIC_SERVER"] = testServerURL

	// 1. Create a relic
	content := "Original content to fork"
	stdin := strings.NewReader(content)
	stdout, _, _, _ := runCLIWithStdin(t, stdin, env, "-", "-o", "json")
	var orig RelicJSONResponse
	json.Unmarshal([]byte(stdout), &orig)

	// 2. Fork the relic
	stdout, stderr, err, exitCode := runCLI(t, env, "fork", orig.ID, "-o", "json", "--name", "Forked Relic")
	if err != nil {
		t.Fatalf("fork failed: %v, stderr: %s", err, stderr)
	}
	if exitCode != 0 {
		t.Fatalf("expected exit code 0, got %d", exitCode)
	}

	var fork RelicJSONResponse
	if err := json.Unmarshal([]byte(stdout), &fork); err != nil {
		t.Fatalf("failed to parse fork response: %v, stdout: %s", err, stdout)
	}

	if fork.ID == "" {
		t.Fatal("forked ID is empty")
	}
	if fork.ForkOf != orig.ID {
		t.Errorf("expected fork_of to be %s, got %s", orig.ID, fork.ForkOf)
	}

	// Check content of fork
	stdout, _, _, _ = runCLI(t, env, "get", fork.ID)
	if stdout != content {
		t.Errorf("expected forked content to be %q, got %q", content, stdout)
	}

	// 3. Delete original (skip prompt using -y)
	stdout, stderr, err, exitCode = runCLI(t, env, "delete", orig.ID, "-y")
	if err != nil {
		t.Fatalf("delete original failed: %v, stderr: %s", err, stderr)
	}
	if exitCode != 0 {
		t.Fatalf("expected exit code 0, got %d", exitCode)
	}

	// Verify original is gone
	_, _, _, exitCode = runCLI(t, env, "info", orig.ID)
	if exitCode == 0 {
		t.Error("expected info to fail on deleted relic")
	}

	// Clean up fork
	_, _, _, _ = runCLI(t, env, "delete", fork.ID, "--yes")
}

func TestCLI_Spaces(t *testing.T) {
	checkServer(t)
	_, env := setupTestEnv(t)
	env["RELIC_SERVER"] = testServerURL

	// We must register the client first (by running an upload or manual command)
	stdin := strings.NewReader("test")
	runCLIWithStdin(t, stdin, env, "-", "-q")

	// 1. Create a space
	spaceName := "Test Space Go CLI"
	stdout, stderr, err, exitCode := runCLI(t, env, "spaces", "create", spaceName, "--visibility", "public", "-o", "json")
	if err != nil {
		t.Fatalf("spaces create failed: %v, stderr: %s", err, stderr)
	}
	if exitCode != 0 {
		t.Fatalf("expected exit code 0, got %d", exitCode)
	}

	var space struct {
		ID         string `json:"id"`
		Name       string `json:"name"`
		Visibility string `json:"visibility"`
	}
	if err := json.Unmarshal([]byte(stdout), &space); err != nil {
		t.Fatalf("failed to parse space JSON: %v, stdout: %s", err, stdout)
	}

	if space.ID == "" {
		t.Fatal("created space ID is empty")
	}
	if space.Name != spaceName {
		t.Errorf("expected space name %q, got %q", spaceName, space.Name)
	}

	// 2. List spaces in JSON format
	stdout, stderr, err, exitCode = runCLI(t, env, "spaces", "list", "-o", "json")
	if err != nil {
		t.Fatalf("spaces list failed: %v, stderr: %s", err, stderr)
	}
	var spacesList struct {
		Spaces []struct {
			ID   string `json:"id"`
			Name string `json:"name"`
		} `json:"spaces"`
	}
	if err := json.Unmarshal([]byte(stdout), &spacesList); err != nil {
		t.Fatalf("failed to parse spaces list JSON: %v, stdout: %s", err, stdout)
	}

	found := false
	for _, s := range spacesList.Spaces {
		if s.ID == space.ID {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("created space %s was not found in spaces list", space.ID)
	}

	// 3. Upload a relic to this space
	stdinRelic := strings.NewReader("relic inside space")
	stdout, stderr, err, exitCode = runCLIWithStdin(t, stdinRelic, env, "-", "--space", space.ID, "-o", "json")
	if err != nil {
		t.Fatalf("failed to upload relic to space: %v, stderr: %s", err, stderr)
	}
	var spaceRelic RelicJSONResponse
	if err := json.Unmarshal([]byte(stdout), &spaceRelic); err != nil {
		t.Fatalf("failed to parse space relic upload JSON: %v", err)
	}

	// Clean up relic
	runCLI(t, env, "delete", spaceRelic.ID, "--yes")

	// 4. Delete the space
	stdout, stderr, err, exitCode = runCLI(t, env, "spaces", "delete", space.ID, "--yes")
	if err != nil {
		t.Fatalf("failed to delete space: %v, stderr: %s", err, stderr)
	}
	if exitCode != 0 {
		t.Fatalf("expected exit code 0, got %d", exitCode)
	}

	// 5. Verify space is deleted
	stdout, _, _, _ = runCLI(t, env, "spaces", "list", "-o", "json")
	var spacesPost struct {
		Spaces []struct {
			ID string `json:"id"`
		} `json:"spaces"`
	}
	json.Unmarshal([]byte(stdout), &spacesPost)
	for _, s := range spacesPost.Spaces {
		if s.ID == space.ID {
			t.Errorf("space %s still exists after deletion", space.ID)
		}
	}
}

func TestCLI_Install(t *testing.T) {
	_, env := setupTestEnv(t)
	tempDir, err := os.MkdirTemp("", "relic-install-test-*")
	if err != nil {
		t.Fatalf("failed to create temp install dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	installPath := filepath.Join(tempDir, "my-relic-binary")

	_, stderr, err, exitCode := runCLI(t, env, "install", "--path", installPath)
	if err != nil {
		t.Fatalf("relic install failed: %v, stderr: %s", err, stderr)
	}
	if exitCode != 0 {
		t.Fatalf("expected exit code 0, got %d", exitCode)
	}

	// Verify that the binary was copied to the destination
	if _, err := os.Stat(installPath); os.IsNotExist(err) {
		t.Errorf("binary was not installed at %s", installPath)
	}
}

func TestCLI_UsageErrors(t *testing.T) {
	_, env := setupTestEnv(t)

	tests := []struct {
		args []string
	}{
		{[]string{"get"}},
		{[]string{"info"}},
		{[]string{"delete"}},
		{[]string{"fork"}},
		{[]string{"spaces", "create"}},
		{[]string{"spaces", "delete"}},
		{[]string{"config", "invalid.key"}},
	}

	for _, tt := range tests {
		t.Run(strings.Join(tt.args, "_"), func(t *testing.T) {
			_, stderr, _, exitCode := runCLI(t, env, tt.args...)
			if exitCode == 0 {
				t.Errorf("expected command %v to fail, but it succeeded", tt.args)
			}
			if !strings.Contains(stderr, "accepts 1") && !strings.Contains(stderr, "Error:") {
				t.Errorf("unexpected stderr: %s", stderr)
			}
		})
	}
}

func TestCLI_PaginationAndFiltering(t *testing.T) {
	checkServer(t)
	_, env := setupTestEnv(t)
	env["RELIC_SERVER"] = testServerURL

	// Upload 3 relics
	var ids []string
	for i := 0; i < 3; i++ {
		stdin := strings.NewReader(fmt.Sprintf("content %d", i))
		access := "public"
		if i == 2 {
			access = "private"
		}
		stdout, _, err, _ := runCLIWithStdin(t, stdin, env, "-", "-o", "json", "-a", access)
		if err != nil {
			t.Fatalf("upload failed: %v", err)
		}
		var r RelicJSONResponse
		json.Unmarshal([]byte(stdout), &r)
		ids = append(ids, r.ID)
	}

	// Clean up at the end
	defer func() {
		for _, id := range ids {
			runCLI(t, env, "delete", id, "-y")
		}
	}()

	// Test limit
	stdout, _, _, _ := runCLI(t, env, "list", "--limit", "2", "-o", "json")
	var listResp struct {
		Relics []RelicJSONResponse `json:"relics"`
	}
	json.Unmarshal([]byte(stdout), &listResp)
	if len(listResp.Relics) != 2 {
		t.Errorf("expected 2 relics, got %d", len(listResp.Relics))
	}

	// Test filter by access level (private should return 1)
	stdout, _, _, _ = runCLI(t, env, "list", "--access-level", "private", "-o", "json")
	var privListResp struct {
		Relics []RelicJSONResponse `json:"relics"`
	}
	json.Unmarshal([]byte(stdout), &privListResp)
	
	privCount := 0
	for _, r := range privListResp.Relics {
		// Only count the ones we just created to avoid interference with other test data if not isolated completely
		for _, id := range ids {
			if r.ID == id {
				privCount++
			}
		}
	}
	if privCount != 1 {
		t.Errorf("expected 1 private relic among our test relics, got %d", privCount)
	}
}

func TestCLI_InteractiveDelete(t *testing.T) {
	checkServer(t)
	_, env := setupTestEnv(t)
	env["RELIC_SERVER"] = testServerURL

	// Upload a relic
	stdin := strings.NewReader("content")
	stdout, _, _, _ := runCLIWithStdin(t, stdin, env, "-", "-o", "json")
	var r RelicJSONResponse
	json.Unmarshal([]byte(stdout), &r)

	// Test NO answer
	stdinNo := strings.NewReader("n\n")
	stdout, _, _, exitCode := runCLIWithStdin(t, stdinNo, env, "delete", r.ID)
	if exitCode != 0 {
		t.Errorf("expected 0 exit code on cancel, got %d", exitCode)
	}
	if !strings.Contains(stdout, "Cancelled") {
		t.Errorf("expected Cancelled message, got: %s", stdout)
	}

	// Verify still exists
	_, _, _, exitCode = runCLI(t, env, "info", r.ID)
	if exitCode != 0 {
		t.Errorf("relic should still exist but info failed")
	}

	// Test YES answer
	stdinYes := strings.NewReader("y\n")
	_, _, _, exitCode = runCLIWithStdin(t, stdinYes, env, "delete", r.ID)
	if exitCode != 0 {
		t.Errorf("expected 0 exit code on yes, got %d", exitCode)
	}

	// Verify it is gone
	_, _, _, exitCode = runCLI(t, env, "info", r.ID)
	if exitCode == 0 {
		t.Errorf("relic should have been deleted, but info succeeded")
	}
}

func TestCLI_QuietMode(t *testing.T) {
	checkServer(t)
	_, env := setupTestEnv(t)
	env["RELIC_SERVER"] = testServerURL

	// Upload with -q
	stdin := strings.NewReader("content")
	stdout, stderr, err, exitCode := runCLIWithStdin(t, stdin, env, "-", "-q")
	if err != nil || exitCode != 0 {
		t.Fatalf("quiet upload failed")
	}
	urlOutput := strings.TrimSpace(stdout)
	if len(urlOutput) == 0 || strings.Contains(urlOutput, " ") {
		t.Errorf("expected quiet output to be exactly the URL, got %q", urlOutput)
	}
	if len(stderr) > 0 {
		t.Errorf("expected empty stderr, got %q", stderr)
	}

	parts := strings.Split(urlOutput, "/")
	id := parts[len(parts)-1]

	// Delete with -q -y
	stdout, stderr, err, exitCode = runCLI(t, env, "delete", id, "-q", "-y")
	if err != nil || exitCode != 0 {
		t.Fatalf("quiet delete failed: %v, stderr: %s", err, stderr)
	}
	if len(strings.TrimSpace(stdout)) > 0 {
		t.Errorf("expected empty stdout on quiet delete, got %q", stdout)
	}
}

func TestCLI_ForkToSpace(t *testing.T) {
	checkServer(t)
	_, env := setupTestEnv(t)
	env["RELIC_SERVER"] = testServerURL

	// Register client
	runCLIWithStdin(t, strings.NewReader("dummy"), env, "-", "-q")

	// Create a space
	stdout, _, err, _ := runCLI(t, env, "spaces", "create", "ForkSpace", "-o", "json")
	if err != nil {
		t.Fatalf("spaces create failed: %v", err)
	}
	var space struct {
		ID string `json:"id"`
	}
	json.Unmarshal([]byte(stdout), &space)

	// Upload original
	stdin := strings.NewReader("content to fork")
	stdout, _, _, _ = runCLIWithStdin(t, stdin, env, "-", "-o", "json")
	var orig RelicJSONResponse
	json.Unmarshal([]byte(stdout), &orig)

	// Fork into space
	stdout, _, err, _ = runCLI(t, env, "fork", orig.ID, "--space", space.ID, "-o", "json")
	if err != nil {
		t.Fatalf("fork to space failed: %v", err)
	}
	var fork RelicJSONResponse
	json.Unmarshal([]byte(stdout), &fork)

	// List spaces and check relic count or fetch the space (API ListSpaces returning relic counts)
	stdout, _, _, _ = runCLI(t, env, "spaces", "list", "-o", "json")
	var spacesList struct {
		Spaces []struct {
			ID         string `json:"id"`
			RelicCount int    `json:"relic_count"`
		} `json:"spaces"`
	}
	json.Unmarshal([]byte(stdout), &spacesList)
	found := false
	for _, s := range spacesList.Spaces {
		if s.ID == space.ID {
			found = true
			if s.RelicCount != 1 {
				t.Errorf("expected space to have 1 relic, got %d", s.RelicCount)
			}
		}
	}
	if !found {
		t.Errorf("space not found in list")
	}

	// Clean up
	runCLI(t, env, "delete", orig.ID, "-y")
	runCLI(t, env, "delete", fork.ID, "-y")
	runCLI(t, env, "spaces", "delete", space.ID, "-y")
}

func TestCLI_UploadErrors(t *testing.T) {
	checkServer(t)
	_, env := setupTestEnv(t)
	env["RELIC_SERVER"] = testServerURL

	// Try uploading a non-existent file
	_, stderr, _, exitCode := runCLI(t, env, "non_existent_file_12345.txt")
	if exitCode == 0 {
		t.Errorf("expected upload of non-existent file to fail")
	}
	if !strings.Contains(stderr, "no such file or directory") && !strings.Contains(stderr, "Cannot open file") && !strings.Contains(stderr, "File not found") {
		t.Errorf("expected error about missing file, got: %s", stderr)
	}
}


