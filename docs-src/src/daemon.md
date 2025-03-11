# daemon

Voice command daemon using Whisper and Yabai for Mac OS X control.
Unified version combining features of original and refactored implementations.

Source: `daemon.py`

## Class: VoiceControlDaemon

Main daemon class for voice control system.

## Function: `__init__(self)`

Initialize the daemon.

## Function: `_setup_logging(self)`

Set up logging configuration.

## Function: `start(self)`

Start the daemon.

## Function: `stop(self)`

Stop the daemon.

## Function: `_signal_handler(self, sig, frame)`

Handle termination signals.

## Function: `_initialize_components(self)`

Initialize all system components.

## Function: `_show_startup_banner(self)`

Show startup banner with system information.

## Function: `_delayed_start(self)`

Start continuous listening after a delay.
