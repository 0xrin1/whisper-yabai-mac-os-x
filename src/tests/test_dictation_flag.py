#!/usr/bin/env python3
"""
Debug script to test dictation mode flag passing
"""

import os
import time
import tempfile
import queue
import threading
import pyautogui
import subprocess
import sys

# Create a test queue
TEST_QUEUE = queue.Queue()


def simulate_recording(text, dictation_mode=False):
    """Simulate recording and add to queue"""
    print(f"Simulating recording with text: '{text}'")

    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
    temp_filename = temp_file.name
    temp_file.close()

    # Write text to file
    with open(temp_filename, "w") as f:
        f.write(text)

    print(f"Created temp file: {temp_filename}")

    # Add to queue with dictation flag
    if dictation_mode:
        print("Adding to queue with dictation flag=True")
        TEST_QUEUE.put((temp_filename, True))
    else:
        print("Adding to queue with dictation flag=False")
        TEST_QUEUE.put(temp_filename)


def process_queue():
    """Process items from the queue"""
    while True:
        # Get item from queue
        item = TEST_QUEUE.get()

        if item is None:
            print("Found None in queue, exiting")
            break

        # Check if dictation mode
        is_dictation_mode = False
        file_path = item

        if isinstance(item, tuple):
            file_path = item[0]
            is_dictation_mode = item[1]
            print(f"Got tuple from queue: {file_path}, dictation={is_dictation_mode}")
        else:
            print(f"Got string from queue: {file_path}, dictation={is_dictation_mode}")

        # Read the file
        with open(file_path, "r") as f:
            text = f.read()

        print(f"Read text from file: '{text}'")

        # Process based on mode
        if is_dictation_mode:
            print("DICTATION MODE: Attempting to type text")

            # Try to paste using clipboard
            try:
                print("Using clipboard method")
                process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                process.communicate(text.encode("utf-8"))
                time.sleep(0.5)

                # Give some time for user to position cursor
                print("Will paste in 3 seconds...")
                for i in range(3, 0, -1):
                    print(f"{i}...")
                    time.sleep(1)

                print("Pasting now...")
                pyautogui.hotkey("command", "v")
                print("Paste command sent")
            except Exception as e:
                print(f"Error pasting: {e}")
        else:
            print(f"COMMAND MODE: Would process command '{text}'")

        # Clean up
        try:
            os.remove(file_path)
            print(f"Removed temp file: {file_path}")
        except:
            print(f"Could not remove temp file: {file_path}")

        TEST_QUEUE.task_done()


if __name__ == "__main__":
    print("Dictation Flag Testing Utility")
    print("=============================")

    # Start processing thread
    processor = threading.Thread(target=process_queue, daemon=True)
    processor.start()

    # Test with dictation mode
    simulate_recording("This is a test of dictation mode", dictation_mode=True)

    # Wait for queue to empty
    TEST_QUEUE.join()

    print("Test completed!")
    TEST_QUEUE.put(None)  # Signal to exit
    processor.join(timeout=1)
