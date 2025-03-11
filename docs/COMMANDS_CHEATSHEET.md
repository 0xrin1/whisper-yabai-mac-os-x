# Voice Control Command Cheatsheet

This document provides a quick reference for available voice commands in your voice control system.

## Mode Activation

| Mode | Activation Method |
|------|------------------|
| Dictation Mode | Default - just speak naturally and words will be typed at cursor |
| Command Mode | Say "jarvis" to activate command mode, then speak your command |

## Custom Voice Model

| Command | Description |
|---------|-------------|
| `python src/voice_training.py` | Run voice training utility to record voice samples |
| `./create_voice_model.sh` | Create custom voice model from existing samples |
| `rm voice_models/active_model.json` | Switch back to default system voices |
| `python -c "import src.speech_synthesis as speech; speech.test_voices()"` | Test all available voices including your custom voice |

## Hotkeys

| Hotkey | Action |
|--------|--------|
| Ctrl+Shift+Space | Activate voice command mode - listens for a command to execute |
| Ctrl+Shift+D | Activate dictation mode - transcribes speech directly to text at cursor position |

## Application Launchers

| Command | Action |
|---------|--------|
| "browser" or "brave" | Open Brave Browser |
| "cursor" | Open Cursor IDE |
| "vim" | Open Ghostty (for Vim use) |
| "terminal" or "ghostty" | Open Ghostty Terminal |
| "mail" or "email" | Open Mail app |
| "calendar" | Open Calendar app |

## Communication Apps

| Command | Action |
|---------|--------|
| "telegram" | Open Telegram |
| "whatsapp" | Open WhatsApp |
| "slack" | Open Slack |
| "messages" or "chat" | Open Messages |

## Window Management (Yabai)

| Command | Action |
|---------|--------|
| "full" | Toggle fullscreen for current window |
| "focus left/right/up/down" | Focus window in specified direction |
| "swap left/right/up/down" | Swap window with one in specified direction |
| "grow" or "shrink" | Resize window horizontally |
| "grow height" or "shrink height" | Resize window vertically |
| "space one" through "space five" | Switch to workspace 1-5 |
| "send to space one" through "send to space five" | Move window to workspace 1-5 |
| "balance" | Balance window layout |
| "float" | Toggle float for window |
| "split vertical" | Split window vertically |
| "split horizontal" | Split window horizontally |

## Common Keyboard Shortcuts

| Command | Action |
|---------|--------|
| "save" | Cmd+S (Save) |
| "undo" | Cmd+Z (Undo) |
| "redo" | Cmd+Shift+Z (Redo) |
| "copy" | Cmd+C (Copy) |
| "paste" | Cmd+V (Paste) |
| "cut" | Cmd+X (Cut) |
| "select all" | Cmd+A (Select all) |
| "find" | Cmd+F (Find) |
| "new tab" | Cmd+T (New tab) |
| "close tab" | Cmd+W (Close tab) |

## System Controls

| Command | Action |
|---------|--------|
| "screenshot" | Take screenshot (portion of screen) |
| "screenshot window" | Take screenshot of window |
| "volume up/down" | Adjust volume |
| "mute" | Mute audio |
| "lock screen" | Lock the screen |

## Vim Commands

| Command | Action |
|---------|--------|
| "vim save" | Save file in Vim (:w) |
| "vim quit" | Quit Vim (:q) |
| "vim save and quit" | Save and quit Vim (:wq) |
| "vim insert" | Enter insert mode (i) |
| "vim normal" | Enter normal mode (Esc) |

## Development

| Command | Action |
|---------|--------|
| "build" | Build project (Cmd+B) |
| "run" | Run project (Cmd+R) |
| "debug" | Debug project (Cmd+D) |
| "stop" | Stop execution (Cmd+.) |
| "comment" | Comment/uncomment line (Cmd+/) |

## Web Resources

| Command | Action |
|---------|--------|
| "github" | Open GitHub |
| "google" | Open Google |
| "stack overflow" | Open Stack Overflow |
| "youtube" | Open YouTube |

This is just a subset of all available commands. For a complete list, see the `commands.json` file.
