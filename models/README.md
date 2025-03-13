# Models Directory

Place your GGUF format LLM models in this directory for natural language command interpretation.

## Recommended Models

### Currently Available Models

This directory contains the following models that you can use with the system:

1. **Llama-2-7B-Chat** (Default)
   - A 7 billion parameter model optimized for chat interactions
   - Quantized for efficient CPU inference
   - File: `llama-2-7b-chat.Q4_K_M.gguf`

2. **TinyLlama-1.1B-Chat**
   - A smaller 1.1 billion parameter model for low-resource systems
   - Faster inference with reduced accuracy
   - File: `tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf`

### Optional: Qwen2 Model

For even better command interpretation, you can download the Qwen2-Instruct model:

1. Download the quantized model from Hugging Face:
   ```
   curl -L "https://huggingface.co/TheBloke/Qwen2-7B-Instruct-GGUF/resolve/main/qwen2-7b-instruct.Q4_K_M.gguf" -o qwen2_7b_instruct.Q4_K_M.gguf
   ```

2. Set the model path in your `.env` file:
   ```
   LLM_MODEL_PATH=models/qwen2_7b_instruct.Q4_K_M.gguf
   ```

### Alternative Models

If the Qwen2 model is too resource-intensive, you can use one of these alternatives:

1. For lower-resource systems:
   - TinyLlama (~1.1B parameters): [TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf](https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf)

2. For medium-resource systems:
   - Llama-2-7B: [Llama-2-7B-Chat.Q4_K_M.gguf](https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf)

## Performance Comparison

The Qwen2-DeepSeek model provides significantly better command interpretation than the default TinyLlama model:

- Larger context window (4096 tokens vs 2048)
- Better accuracy in command recognition
- Improved handling of ambiguous commands
- More robust language understanding
- Optimized prompting for command parsing
- Better JSON parsing abilities for dynamic responses

## GPU Acceleration

To enable GPU acceleration for the LLM, set the `LLM_GPU_LAYERS` environment variable:

```bash
export LLM_GPU_LAYERS=32  # Adjust based on your GPU memory
```

This will offload some of the model computation to the GPU for faster inference.

## Whisper ASR Models

Whisper models will be downloaded automatically when you first run the application.

By default, the system uses the "large-v3" model. If you want to use a different size model, you can set the `WHISPER_MODEL_SIZE` environment variable or update the MODEL_SIZE in config.json to one of:
- `tiny` (fastest, least accurate)
- `base` (faster, less accurate)
- `small` (balance of speed and accuracy)
- `medium` (good accuracy with moderate performance)
- `large` (excellent accuracy, slower)
- `large-v2` (improved version of large)
- `large-v3` (default, most accurate, latest version)
