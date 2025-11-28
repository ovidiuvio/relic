package ui

import (
	"bufio"
	"fmt"
	"os"
	"strings"
)

// Confirm prompts the user for yes/no confirmation
func Confirm(message string) bool {
	reader := bufio.NewReader(os.Stdin)
	fmt.Printf("%s [y/N]: ", message)

	response, err := reader.ReadString('\n')
	if err != nil {
		return false
	}

	response = strings.TrimSpace(strings.ToLower(response))
	return response == "y" || response == "yes"
}

// PromptPassword prompts the user for a password
func PromptPassword(message string) (string, error) {
	reader := bufio.NewReader(os.Stdin)
	fmt.Printf("%s: ", message)

	password, err := reader.ReadString('\n')
	if err != nil {
		return "", err
	}

	return strings.TrimSpace(password), nil
}
