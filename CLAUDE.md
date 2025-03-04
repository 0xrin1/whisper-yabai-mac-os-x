# Whisper Voice Control Coding Guidelines

## Commands
- Run daemon: `python src/daemon.py`
- Run simplified daemon: `python src/simple_dictation.py`
- Check permissions: `python src/permissions_check.py`
- Test specific module: `python src/test_*.py`
- Install deps: `pip install -r requirements.txt`

## Code Style
- Use 4-space indentation
- Follow PEP 8 naming conventions (snake_case for functions/variables)
- Class names in PascalCase
- Constants in UPPER_SNAKE_CASE
- Import order: standard lib -> third-party -> local modules
- Type annotations for function parameters and returns
- Document classes and functions with docstrings
- Use context managers for resource handling (with statements)
- Exception handling with specific exception types
- Log errors with appropriate logging levels
- Use f-strings for string formatting