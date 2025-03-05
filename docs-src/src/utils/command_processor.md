# command_processor

Command processor module for voice control system.
Executes system commands based on voice input.

Source: `utils/command_processor.py`

## Class: CommandProcessor

Processes voice commands and executes corresponding actions.

## Function: `__init__(self)`

Initialize command processor.

## Function: `load_commands(self)`

Load command mappings from config/commands.json if it exists.

## Function: `has_command(self, command)`

Check if a command exists.
        
        Args:
            command: Command name to check
            
        Returns:
            bool: True if command exists, False otherwise

## Function: `execute(self, command, args)`

Execute a command with args.
        
        Args:
            command: Command to execute
            args: Arguments for the command
            
        Returns:
            bool: True if command executed successfully

## Function: `parse_and_execute(self, text)`

Parse and execute a command string.
        
        Args:
            text: Command text to parse
            
        Returns:
            bool: True if command executed successfully

## Function: `execute_shell_command(self, command)`

Execute a shell command.
        
        Args:
            command: Shell command to execute
            
        Returns:
            bool: True if command succeeded, False otherwise

## Function: `open_application(self, args)`

Open an application.
        
        Args:
            args: List of arguments, first being the app name
            
        Returns:
            bool: True if application opened successfully

## Function: `focus_application(self, args)`

Focus on an application using Yabai.
        
        Args:
            args: List of arguments, first being the app name
            
        Returns:
            bool: True if application focused successfully

## Function: `type_text(self, args)`

Type text.
        
        Args:
            args: List of arguments, joined to form the text to type
            
        Returns:
            bool: True if text typed successfully

## Function: `move_window(self, args)`

Move the focused window to a position.
        
        Args:
            args: List of arguments, first being the direction
            
        Returns:
            bool: True if window moved successfully

## Function: `resize_window(self, args)`

Resize the focused window.
        
        Args:
            args: List of arguments, first being the direction
            
        Returns:
            bool: True if window resized successfully

## Function: `move_to_space(self, args)`

Move the focused window to a space.
        
        Args:
            args: List of arguments, first being the space number
            
        Returns:
            bool: True if window moved successfully

## Function: `maximize_window(self, args)`

Maximize the focused window.
        
        Args:
            args: List of arguments (not used)
            
        Returns:
            bool: True if window maximized successfully

## Function: `close_window(self, args)`

Close the focused window.
        
        Args:
            args: List of arguments (not used)
            
        Returns:
            bool: True if window closed successfully

## Function: `click_mouse(self, args)`

Click the mouse at the current position.
        
        Args:
            args: List of arguments (not used)
            
        Returns:
            bool: True if mouse clicked successfully

