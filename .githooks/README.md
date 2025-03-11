# Git Hooks for Whisper Voice Control

This directory contains git hooks that help maintain code quality and prevent common issues.

## Available Hooks

- **pre-commit**: Runs before each commit to ensure code quality
  - Checks Python syntax
  - Verifies imports work
  - Tests core functionality
  - Warns about problematic patterns (print statements, TODOs, hardcoded paths)
  - Warns about large files

## Installation

To install these hooks, run the following commands from the project root:

```bash
# Make hooks executable
chmod +x .githooks/pre-commit

# Configure git to use these hooks
git config core.hooksPath .githooks
```

## Usage

The hooks will run automatically when you perform git operations. For example, the pre-commit hook will run whenever you attempt to make a commit.

If a hook fails, it will abort the operation and display an error message explaining what went wrong.

## Bypassing Hooks

In rare cases where you need to bypass a hook (not recommended), you can use the `--no-verify` flag:

```bash
git commit --no-verify -m "Your commit message"
```
