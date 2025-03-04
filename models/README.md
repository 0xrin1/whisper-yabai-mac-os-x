# Models Directory

Place your GGUF format LLM models in this directory for natural language command interpretation.

## Recommended Models

For natural language command interpretation, you'll need at least one GGUF format model:

1. For lower-resource systems:
   - TinyLlama (~1.1B parameters): [TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf](https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf)

2. For systems with more resources:
   - Llama-2-7B: [Llama-2-7B-Chat.Q4_K_M.gguf](https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf)

## Usage

After downloading the model, update your `.env` file to point to the correct model path:

```
LLM_MODEL_PATH=models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
```

Whisper models will be downloaded automatically when you first run the application.