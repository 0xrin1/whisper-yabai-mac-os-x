#!/usr/bin/env python3
"""
Unit tests for the state manager module.
Tests state management functionality.
"""

import os
import sys
import time
import unittest
from unittest.mock import patch, MagicMock, call

# Add the src directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module to test
from src.core.state_manager import StateManager

class TestStateManager(unittest.TestCase):
    """Test state management functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a fresh StateManager for each test
        self.state_manager = StateManager()
    
    def test_recording_state(self):
        """Test recording state functionality."""
        # Test initial state
        self.assertFalse(self.state_manager.is_recording())
        
        # Test starting recording
        self.state_manager.start_recording()
        self.assertTrue(self.state_manager.is_recording())
        self.assertGreater(self.state_manager.recording_start_time, 0)
        
        # Test stopping recording
        self.state_manager.stop_recording()
        self.assertFalse(self.state_manager.is_recording())
    
    def test_mute_state(self):
        """Test mute state functionality."""
        # Test initial state
        self.assertFalse(self.state_manager.is_muted())
        
        # Test toggling mute
        self.state_manager.toggle_mute()
        self.assertTrue(self.state_manager.is_muted())
        
        # Test toggling back
        self.state_manager.toggle_mute()
        self.assertFalse(self.state_manager.is_muted())
    
    def test_key_state(self):
        """Test key state functionality."""
        # Test initial key states
        for key in ('ctrl', 'shift', 'alt', 'cmd', 'space'):
            self.assertFalse(self.state_manager.key_states[key])
        
        # Test setting key state
        self.state_manager.set_key_state('ctrl', True)
        self.state_manager.set_key_state('shift', True)
        self.assertTrue(self.state_manager.key_states['ctrl'])
        self.assertTrue(self.state_manager.key_states['shift'])
        self.assertFalse(self.state_manager.key_states['space'])
        
        # Test checking hotkey combinations
        self.assertTrue(self.state_manager.check_hotkey('ctrl', 'shift'))
        self.assertFalse(self.state_manager.check_hotkey('ctrl', 'shift', 'space'))
        self.assertFalse(self.state_manager.check_hotkey('alt', 'cmd'))
    
    def test_audio_queue(self):
        """Test audio queue functionality."""
        # Enqueue some audio files
        self.state_manager.enqueue_audio("test1.wav")
        self.state_manager.enqueue_audio("test2.wav", is_dictation=True)
        self.state_manager.enqueue_audio("test3.wav", is_trigger=True)
        
        # Test getting items from queue
        audio1 = self.state_manager.get_next_audio()
        self.assertEqual(audio1[0], "test1.wav")
        self.assertFalse(audio1[1])  # is_dictation
        self.assertFalse(audio1[2])  # is_trigger
        
        audio2 = self.state_manager.get_next_audio()
        self.assertEqual(audio2[0], "test2.wav")
        self.assertTrue(audio2[1])   # is_dictation
        self.assertFalse(audio2[2])  # is_trigger
        
        audio3 = self.state_manager.get_next_audio()
        self.assertEqual(audio3[0], "test3.wav")
        self.assertFalse(audio3[1])  # is_dictation
        self.assertTrue(audio3[2])   # is_trigger
    
    def test_non_blocking_get_next_audio(self):
        """Test non-blocking get_next_audio behavior."""
        # Test with empty queue
        result = self.state_manager.get_next_audio(block=False)
        self.assertIsNone(result)
        
        # Test with timeout
        start_time = time.time()
        result = self.state_manager.get_next_audio(block=True, timeout=0.1)
        elapsed = time.time() - start_time
        self.assertIsNone(result)
        self.assertLess(elapsed, 0.2)  # Should be around 0.1s
    
    def test_mute_callbacks(self):
        """Test mute state change callbacks."""
        # Create mock callbacks
        callback1 = MagicMock()
        callback2 = MagicMock()
        
        # Register callbacks
        self.state_manager.on_mute_change(callback1)
        self.state_manager.on_mute_change(callback2)
        
        # Toggle mute and check callbacks
        self.state_manager.toggle_mute()
        callback1.assert_called_once_with(True)
        callback2.assert_called_once_with(True)
        
        # Reset mocks and toggle again
        callback1.reset_mock()
        callback2.reset_mock()
        self.state_manager.toggle_mute()
        callback1.assert_called_once_with(False)
        callback2.assert_called_once_with(False)
        
        # Test duplicate registration is ignored
        callback1.reset_mock()
        self.state_manager.on_mute_change(callback1)  # Try to register again
        self.state_manager.toggle_mute()
        callback1.assert_called_once_with(True)  # Should still be called only once
    
    def test_recording_callbacks(self):
        """Test recording state change callbacks."""
        # Create mock callbacks
        callback = MagicMock()
        
        # Register callback
        self.state_manager.on_recording_change(callback)
        
        # Start recording and check callback
        self.state_manager.start_recording()
        callback.assert_called_once_with(True)
        
        # Reset mock and stop recording
        callback.reset_mock()
        self.state_manager.stop_recording()
        callback.assert_called_once_with(False)
    
    def test_callback_error_handling(self):
        """Test error handling in callbacks."""
        # Create a callback that raises an exception
        bad_callback = MagicMock(side_effect=Exception("Test exception"))
        
        # Register callback
        self.state_manager.on_mute_change(bad_callback)
        
        # Toggle mute should not raise the exception
        with patch('logging.Logger.error') as mock_error:
            self.state_manager.toggle_mute()
            # Check that error was logged
            mock_error.assert_called_with(
                "Error in mute callback: Test exception"
            )
        
        # Same test for recording callback
        bad_callback = MagicMock(side_effect=Exception("Test exception"))
        self.state_manager.on_recording_change(bad_callback)
        
        with patch('logging.Logger.error') as mock_error:
            self.state_manager.start_recording()
            # Check that error was logged
            mock_error.assert_called_with(
                "Error in recording callback: Test exception"
            )
    
    def test_trigger_buffer_manipulation(self):
        """Test trigger buffer functionality."""
        # Initial state
        self.assertEqual(self.state_manager.trigger_buffer, [])
        
        # Add to buffer
        self.state_manager.trigger_buffer.append("sample1")
        self.state_manager.trigger_buffer.append("sample2")
        
        self.assertEqual(len(self.state_manager.trigger_buffer), 2)
        self.assertEqual(self.state_manager.trigger_buffer[0], "sample1")
        self.assertEqual(self.state_manager.trigger_buffer[1], "sample2")

if __name__ == '__main__':
    unittest.main()