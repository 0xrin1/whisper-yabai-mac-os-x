#!/usr/bin/env python3
"""
Command processor module for voice control system.
Executes system commands based on voice input.
"""

import os
import json
import logging
import subprocess
import pyautogui

logger = logging.getLogger('command-processor')

class CommandProcessor:
    """Processes voice commands and executes corresponding actions."""
    
    def __init__(self):
        """Initialize command processor."""
        self.commands = {}
        self.load_commands()
    
    def load_commands(self):
        """Load command mappings from commands.json if it exists."""
        default_commands = {
            "open": self.open_application,
            "focus": self.focus_application,
            "type": self.type_text,
            "move": self.move_window,
            "resize": self.resize_window,
            "space": self.move_to_space,
            "maximize": self.maximize_window,
            "close": self.close_window,
            "click": self.click_mouse,
        }
        
        try:
            with open('commands.json', 'r') as f:
                custom_data = json.load(f)
                if 'custom_commands' in custom_data:
                    default_commands.update(custom_data['custom_commands'])
                else:
                    default_commands.update(custom_data)
        except FileNotFoundError:
            logger.warning("commands.json not found, using default commands only")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing commands.json: {e}")
        
        self.commands = default_commands
    
    def has_command(self, command):
        """Check if a command exists.
        
        Args:
            command: Command name to check
            
        Returns:
            bool: True if command exists, False otherwise
        """
        return command in self.commands
    
    def execute(self, command, args):
        """Execute a command with args.
        
        Args:
            command: Command to execute
            args: Arguments for the command
            
        Returns:
            bool: True if command executed successfully
        """
        if command not in self.commands:
            logger.warning(f"Unknown command: {command}")
            return False
            
        cmd_action = self.commands[command]
        if callable(cmd_action):
            try:
                cmd_action(args)
                # Show success notification
                from toast_notifications import notify_command_executed
                notify_command_executed(f"{command} {' '.join(args)}")
                return True
            except Exception as e:
                logger.error(f"Error executing command '{command}': {e}")
                from toast_notifications import notify_error
                notify_error(f"Error executing '{command}': {str(e)}")
                return False
        else:
            # Handle string command
            cmd_str = cmd_action
            
            # Check if command contains pyautogui
            if "pyautogui." in cmd_str:
                try:
                    # We need to handle pyautogui commands directly
                    if "pyautogui.hotkey" in cmd_str:
                        # Extract the hotkey arguments
                        key_args = cmd_str.split("pyautogui.hotkey(")[1].split(")")[0]
                        keys = [k.strip("'\" ") for k in key_args.split(",")]
                        logger.info(f"Executing hotkey: {keys}")
                        pyautogui.hotkey(*keys)
                        
                        from toast_notifications import notify_command_executed
                        notify_command_executed(f"Hotkey: {'+'.join(keys)}")
                        return True
                    elif "pyautogui.write" in cmd_str:
                        # Extract the text to write
                        text = cmd_str.split("pyautogui.write(")[1].split(")")[0].strip("'\" ")
                        logger.info(f"Writing text: {text}")
                        pyautogui.write(text)
                        
                        from toast_notifications import notify_command_executed
                        notify_command_executed(f"Type: {text}")
                        return True
                    else:
                        logger.error(f"Unsupported pyautogui command: {cmd_str}")
                        from toast_notifications import notify_error
                        notify_error(f"Unsupported command: {cmd_str}")
                        return False
                except Exception as e:
                    logger.error(f"Error executing pyautogui command: {e}")
                    from toast_notifications import notify_error
                    notify_error(f"Error with keyboard/mouse command: {str(e)}")
                    return False
            else:
                # Handle shell command (Yabai or other)
                success = self.execute_shell_command(cmd_str)
                if success:
                    from toast_notifications import notify_command_executed
                    notify_command_executed(f"{command}: {cmd_str}")
                    return True
                else:
                    from toast_notifications import notify_error
                    notify_error(f"Failed to run: {cmd_str}")
                    return False
    
    def parse_and_execute(self, text):
        """Parse and execute a command string.
        
        Args:
            text: Command text to parse
            
        Returns:
            bool: True if command executed successfully
        """
        # Clean and normalize the text
        clean_text = text.lower().strip()
        
        if not clean_text:
            logger.warning("Empty command received")
            from toast_notifications import notify_error
            notify_error("Empty command received")
            return False
        
        # Check for dictation mode command first
        dictation_fragments = ["dictate", "dictation", "dict", "type", "write", "text", "note"]
        for fragment in dictation_fragments:
            if fragment in clean_text:
                logger.info(f"Detected dictation command: '{fragment}' in '{clean_text}'")
                
                # Start dictation mode
                from trigger_detection import TriggerDetector
                detector = TriggerDetector()
                detector._start_recording_thread('dictation', force=True)
                return True
        
        # Simple command parsing
        # Look for known command patterns
        if "open" in clean_text and " " in clean_text:
            # Extract app name after "open"
            app_part = clean_text[clean_text.find("open") + 4:].strip()
            logger.info(f"Detected open command for app: {app_part}")
            return self.open_application([app_part])
            
        if "browser" in clean_text or "safari" in clean_text or "chrome" in clean_text:
            logger.info("Detected browser command")
            return self.execute_shell_command("open -a 'Safari'")
            
        if "terminal" in clean_text:
            logger.info("Detected terminal command")
            return self.execute_shell_command("open -a 'Terminal'")
            
        if "maximize" in clean_text or "full screen" in clean_text:
            logger.info("Detected maximize command")
            return self.maximize_window([])
        
        # Standard command processing
        parts = clean_text.split()
        
        if not parts:
            logger.warning("Empty command parts after splitting")
            return False
        
        # Extract the command and arguments
        command = parts[0]
        args = parts[1:]
        
        # Execute the parsed command
        if command in self.commands:
            return self.execute(command, args)
        else:
            logger.warning(f"Unknown command: {command}, looking in full text for commands")
            
            # Try to find command in custom_commands even if not at start of sentence
            for cmd_name in self.commands.keys():
                if isinstance(cmd_name, str) and cmd_name in clean_text:
                    logger.info(f"Found command '{cmd_name}' in text")
                    return self.execute(cmd_name, [])
            
            # No command found
            from toast_notifications import notify_error
            notify_error(f"Unknown command: {command}")
            return False
    
    def execute_shell_command(self, command):
        """Execute a shell command.
        
        Args:
            command: Shell command to execute
            
        Returns:
            bool: True if command succeeded, False otherwise
        """
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            logger.info(f"Command executed: {result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Command execution failed: {e.stderr}")
            return False
    
    def open_application(self, args):
        """Open an application.
        
        Args:
            args: List of arguments, first being the app name
            
        Returns:
            bool: True if application opened successfully
        """
        if not args:
            return False
            
        app_name = " ".join(args)
        logger.info(f"Opening application: {app_name}")
        
        # Use open command to launch application
        return self.execute_shell_command(f"open -a '{app_name}'")
    
    def focus_application(self, args):
        """Focus on an application using Yabai.
        
        Args:
            args: List of arguments, first being the app name
            
        Returns:
            bool: True if application focused successfully
        """
        if not args:
            return False
            
        app_name = " ".join(args)
        logger.info(f"Focusing application: {app_name}")
        
        # Use Yabai to focus the application
        return self.execute_shell_command(f"yabai -m window --focus \"$(/usr/bin/grep -i '{app_name}' <(/usr/bin/yabai -m query --windows | /usr/bin/jq -r '.[].app') | head -n1)\"")
    
    def type_text(self, args):
        """Type text.
        
        Args:
            args: List of arguments, joined to form the text to type
            
        Returns:
            bool: True if text typed successfully
        """
        if not args:
            return False
            
        text = " ".join(args)
        logger.info(f"Typing text: {text}")
        
        try:
            pyautogui.write(text)
            return True
        except Exception as e:
            logger.error(f"Error typing text: {e}")
            return False
    
    def move_window(self, args):
        """Move the focused window to a position.
        
        Args:
            args: List of arguments, first being the direction
            
        Returns:
            bool: True if window moved successfully
        """
        if len(args) < 1:
            return False
            
        direction = args[0]
        
        if direction in ["left", "right", "top", "bottom"]:
            return self.execute_shell_command(f"yabai -m window --move {direction}")
        else:
            logger.warning(f"Unknown direction: {direction}")
            return False
    
    def resize_window(self, args):
        """Resize the focused window.
        
        Args:
            args: List of arguments, first being the direction
            
        Returns:
            bool: True if window resized successfully
        """
        if len(args) < 1:
            return False
            
        direction = args[0]
        
        if direction in ["left", "right", "top", "bottom"]:
            return self.execute_shell_command(f"yabai -m window --resize {direction}:20:20")
        else:
            logger.warning(f"Unknown direction: {direction}")
            return False
    
    def move_to_space(self, args):
        """Move the focused window to a space.
        
        Args:
            args: List of arguments, first being the space number
            
        Returns:
            bool: True if window moved successfully
        """
        if not args or not args[0].isdigit():
            return False
            
        space = args[0]
        logger.info(f"Moving window to space: {space}")
        
        return self.execute_shell_command(f"yabai -m window --space {space}")
    
    def maximize_window(self, args):
        """Maximize the focused window.
        
        Args:
            args: List of arguments (not used)
            
        Returns:
            bool: True if window maximized successfully
        """
        logger.info("Maximizing window")
        
        return self.execute_shell_command("yabai -m window --toggle zoom-fullscreen")
    
    def close_window(self, args):
        """Close the focused window.
        
        Args:
            args: List of arguments (not used)
            
        Returns:
            bool: True if window closed successfully
        """
        logger.info("Closing window")
        
        try:
            pyautogui.hotkey('command', 'w')
            return True
        except Exception as e:
            logger.error(f"Error closing window: {e}")
            return False
    
    def click_mouse(self, args):
        """Click the mouse at the current position.
        
        Args:
            args: List of arguments (not used)
            
        Returns:
            bool: True if mouse clicked successfully
        """
        logger.info("Clicking mouse")
        
        try:
            pyautogui.click()
            return True
        except Exception as e:
            logger.error(f"Error clicking mouse: {e}")
            return False

# Create a singleton instance
commands = CommandProcessor()