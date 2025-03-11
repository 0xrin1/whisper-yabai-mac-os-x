# llm_interpreter

LLM-based interpreter for natural language commands.
Uses llama.cpp to run local language models for command processing.

Source: `utils/llm_interpreter.py`

## Class: CommandInterpreter

Interprets natural language commands using a local LLM.
    Translates speech into structured command actions.

## Function: `__init__(self, model_path: Optional[str] = None, n_ctx: int = 4096)`

Initialize the LLM-based command interpreter.

## Function: `_determine_model_type(self)`

Determine the model type based on the filename.

## Function: `_load_model(self)`

Load the LLM model.

## Function: `_get_qwen_prompt_template(self, commands_list, text)`

Get prompt template optimized for Qwen models.

## Function: `_get_deepseek_prompt_template(self, commands_list, text)`

Get prompt template optimized for DeepSeek models.

## Function: `_get_llama_prompt_template(self, commands_list, text)`

Get prompt template for Llama-style models.

## Function: `_get_qwen_dynamic_prompt(self, transcription)`

Get dynamic response prompt for Qwen models.

## Function: `_get_deepseek_dynamic_prompt(self, transcription)`

Get dynamic response prompt for DeepSeek models.

## Function: `_get_llama_dynamic_prompt(self, transcription)`

Get dynamic response prompt for Llama-style models.

## Function: `_fix_json_string(self, json_str)`

Fix common JSON formatting issues in LLM responses.

## Function: `_extract_key_values(self, text)`

Extract key-value pairs from text when JSON parsing fails.

## Function: `test_interpreter()`

Test the command interpreter with sample commands.
