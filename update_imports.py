#!/usr/bin/env python3
"""
Script to update import statements in Python files to reflect the new directory structure.
"""

import os
import re
import sys

# Define the import mappings
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

def process_directory(directory):
    """Process all Python files in a directory and its subdirectories."""
    count = 0
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                update_imports(file_path)
                count += 1
    print(f"Processed {count} Python files")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = "src"
    
    process_directory(directory)