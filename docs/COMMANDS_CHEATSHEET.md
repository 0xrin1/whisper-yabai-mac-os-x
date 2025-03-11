# Voice Control Command Cheatsheet

> **IMPORTANT UPDATE**: The command system has been simplified. All traditional commands have been removed. Now saying "jarvis" followed by your question will directly interact with Claude Code AI. Dictation remains the default mode for any speech not starting with "jarvis".

This document provides information about the voice control system.

## Mode Activation

| Mode | Activation Method |
|------|------------------|
| Dictation Mode | Default - just speak naturally and words will be typed at cursor |
| Cloud Code Mode | Say "jarvis" followed by your question to talk to Claude Code |

## Hotkeys

| Hotkey | Action |
|--------|--------|
| Ctrl+Shift+Space | Activate dictation mode - transcribes speech directly to text at cursor position |
| Ctrl+Shift+D | Activate dictation mode (alternative hotkey) |
| Ctrl+Shift+M | Toggle microphone mute |

## Cloud Code Examples

With Cloud Code integration, you can ask Claude Code to help you with various tasks by saying "jarvis" followed by your request:

| Example Phrase | Description |
|----------------|-------------|
| "jarvis, what's the weather today?" | Ask about the weather |
| "jarvis, tell me a joke" | Request a joke |
| "jarvis, how do I fix this error in my code?" | Get coding help |
| "jarvis, summarize the latest news" | Ask for news summaries |
| "jarvis, explain quantum computing" | Request explanations on topics |
| "jarvis, what's the capital of France?" | Ask factual questions |
| "jarvis, help me debug this JavaScript function" | Get coding assistance |
| "jarvis, write a poem about spring" | Request creative content |

## Dictation Tips

Since dictation is now the default mode, here are some tips for effective dictation:

- Speak clearly and at a moderate pace
- Pause briefly between sentences
- Say "period", "comma", "question mark" etc. for punctuation
- Natural speech works best - no need to speak in an unnatural way
- The system will automatically stop recording after a few seconds of silence
- Dictation works in any application where text can be entered

## Custom Voice Model (for Cloud Code Responses)

You can customize the voice used for Cloud Code responses:

| Command | Description |
|---------|-------------|
| `python src/voice_training.py` | Run voice training utility to record voice samples |
| `./create_voice_model.sh` | Create custom voice model from existing samples |
| `rm voice_models/active_model.json` | Switch back to default system voices |
| `python -c "import src.speech_synthesis as speech; speech.test_voices()"` | Test all available voices including your custom voice |
