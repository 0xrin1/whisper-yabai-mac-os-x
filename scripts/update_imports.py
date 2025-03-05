#!/usr/bin/env python3
"""
Script to update file references in code to reflect the new directory structure.
"""

import os
import re
import sys

# Define the import mappings for Python modules
IMPORT_MAPPINGS = {
    # Core modules
    'src.state_manager': 'src.core.state_manager',
    'src.error_handler': 'src.core.error_handler',
    'src.logging_config': 'src.core.logging_config',
    'src.core_dictation': 'src.core.core_dictation',
    
    # Config modules
    'src.config': 'src.config.config',
    
    # Audio modules
    'src.audio_processor': 'src.audio.audio_processor',
    'src.audio_recorder': 'src.audio.audio_recorder',
    'src.continuous_recorder': 'src.audio.continuous_recorder',
    'src.resource_manager': 'src.audio.resource_manager',
    'src.trigger_detection': 'src.audio.trigger_detection',
    'src.neural_voice_client': 'src.audio.neural_voice_client',
    'src.speech_synthesis': 'src.audio.speech_synthesis',
    'src.voice_training': 'src.audio.voice_training',
    
    # UI modules
    'src.toast_notifications': 'src.ui.toast_notifications',
    
    # Utility modules
    'src.dictation': 'src.utils.dictation',
    'src.simple_dictation': 'src.utils.simple_dictation',
    'src.ultra_simple_dictation': 'src.utils.ultra_simple_dictation',
    'src.direct_typing': 'src.utils.direct_typing',
    'src.hotkey_manager': 'src.utils.hotkey_manager',
    'src.llm_interpreter': 'src.utils.llm_interpreter',
    'src.command_processor': 'src.utils.command_processor',
    'src.assistant': 'src.utils.assistant',
    
    # Test modules remain in the same location
}

# Define the file path mappings
FILE_MAPPINGS = {
    # Config files
    'config/.env': 'config/.env',
    'config/.env.example': 'config/.env.example',
    'config/config.json': 'config/config.json',
    'config/commands.json': 'config/commands.json',
    'config/com.example.whispervoicecontrol.plist': 'config/com.example.whispervoicecontrol.plist',
    
    # Documentation files
    'docs/CLAUDE.md': 'docs/CLAUDE.md',
    'docs/COMMANDS_CHEATSHEET.md': 'docs/COMMANDS_CHEATSHEET.md',
    'docs/NEURAL_VOICE.md': 'docs/NEURAL_VOICE.md',
    'docs/NEURAL_VOICE_GUIDE.md': 'docs/NEURAL_VOICE_GUIDE.md',
    'docs/LICENSE': 'docs/LICENSE',
    'docs/dictation_log.txt.example': 'docs/dictation_log.txt.example',
    
    # Scripts
    'scripts/check_gpu_server.sh': 'scripts/check_gpu_server.sh',
    'scripts/start_voice_control.sh': 'scripts/start_voice_control.sh',
    
    # Neural voice scripts
    'scripts/neural_voice/create_voice_model.sh': 'scripts/neural_voice/create_voice_model.sh',
    'scripts/neural_voice/setup_neural_voice.sh': 'scripts/neural_voice/setup_neural_voice.sh',
    'scripts/neural_voice/test_neural_voice.py': 'scripts/neural_voice/test_neural_voice.py',
    
    # GPU scripts
    'scripts/gpu/check_gpu_server.sh': 'scripts/gpu/check_gpu_server.sh',
    'scripts/gpu/neural_voice_server.py': 'scripts/gpu/neural_voice_server.py',
    'scripts/gpu/retrieve_from_gpu_server.sh': 'scripts/gpu/retrieve_from_gpu_server.sh',
    'scripts/gpu/start_neural_server.sh': 'scripts/gpu/start_neural_server.sh', 
    'scripts/gpu/train_neural_voice.py': 'scripts/gpu/train_neural_voice.py',
    'scripts/gpu/transfer_to_gpu_server.sh': 'scripts/gpu/transfer_to_gpu_server.sh',
    
    # Setup scripts
    'scripts/setup/setup_remote.sh': 'scripts/setup/setup_remote.sh',
}

def update_imports(file_path):
    """Update import statements in a single Python file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Track if we made any changes
    original_content = content
    
    # Update import statements
    for old_import, new_import in IMPORT_MAPPINGS.items():
        # Match both "import src.module" and "from src.module import X"
        content = re.sub(
            rf'(from\s+|import\s+){old_import}(\s+|\.|;|$)',
            rf'\1{new_import}\2',
            content
        )
    
    # Only write back if changes were made
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Updated imports in {file_path}")
    else:
        print(f"No changes needed in {file_path}")
    
    return content != original_content

def update_file_paths(file_path):
    """Update file path references in a file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Track if we made any changes
    original_content = content
    
    # Update file path references
    for old_path, new_path in FILE_MAPPINGS.items():
        # Escape special regex characters in the path
        old_path_escaped = re.escape(old_path)
        
        # Match the path surrounded by various context characters
        for pattern in [
            rf'(["\']){old_path_escaped}(["\'])',  # "path" or 'path'
            rf'(\s+){old_path_escaped}(\s+)',      # path surrounded by whitespace
            rf'(=\s*){old_path_escaped}(\s*)',     # =path or = path
            rf'(\(){old_path_escaped}(\))',        # (path)
            rf'(,\s*){old_path_escaped}(\s*)',     # ,path or , path
            rf'(\[){old_path_escaped}(\])',        # [path]
            rf'(:){old_path_escaped}(\s*)',        # :path
        ]:
            content = re.sub(pattern, rf'\1{new_path}\2', content)
    
    # Only write back if changes were made
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Updated file paths in {file_path}")
        return True
    else:
        print(f"No file path changes needed in {file_path}")
        return False

def process_directory(directory):
    """Process all files in a directory and its subdirectories."""
    count_py = 0
    count_sh = 0
    count_other = 0
    
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            
            # Skip binary files and very large files
            if os.path.getsize(file_path) > 1024 * 1024:  # Skip files larger than 1MB
                continue
                
            try:
                if file.endswith('.py'):
                    # Update both imports and file paths in Python files
                    imports_updated = update_imports(file_path)
                    paths_updated = update_file_paths(file_path)
                    if imports_updated or paths_updated:
                        count_py += 1
                elif file.endswith('.sh'):
                    # Update file paths in shell scripts
                    if update_file_paths(file_path):
                        count_sh += 1
                elif file.endswith(('.md', '.txt', '.json')):
                    # Update file paths in other text files
                    if update_file_paths(file_path):
                        count_other += 1
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
    
    print(f"Updated {count_py} Python files, {count_sh} shell scripts, and {count_other} other files")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        # Process both src directory and other directories
        process_directory("src")
        process_directory("scripts")
        process_directory("config")
        process_directory("docs")
        sys.exit(0)
        
    process_directory(directory)