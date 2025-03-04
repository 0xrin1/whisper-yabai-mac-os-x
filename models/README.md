# Models Directory

Place your GGUF format LLM models in this directory for natural language command interpretation.

## Recommended Models

### NEW RECOMMENDATION: Qwen2-DeepSeek Model

For the best command interpretation performance, we now recommend using the Qwen2-Instruct model based on DeepSeek technology:

1. Download the quantized model from Hugging Face:
   ```
   curl -L "https://huggingface.co/TheBloke/Qwen2-7B-Instruct-GGUF/resolve/main/qwen2-7b-instruct.Q4_K_M.gguf" -o qwen2_deepseek_7b_instruct.Q4_K_M.gguf
   ```
   
   Place the downloaded file in this directory. The correct path should be:
   ```
   models/qwen2_deepseek_7b_instruct.Q4_K_M.gguf
   ```

2. Set the model path in your `.env` file:
   ```
   LLM_MODEL_PATH=models/qwen2_deepseek_7b_instruct.Q4_K_M.gguf
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

By default, the system uses the "tiny" model. If you want to use a different size model, you can set the `WHISPER_MODEL_SIZE` environment variable to one of:
- `tiny` (default)
- `base`
- `small`
- `medium`
- `large`