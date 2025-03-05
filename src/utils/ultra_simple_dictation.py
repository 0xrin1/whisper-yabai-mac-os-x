#!/usr/bin/env python3
"""Ultra simplified dictation system."""

import os
import time
import tempfile
import pyaudio
import wave
import whisper
import pyautogui
import subprocess

def record_audio(duration=5):
    """Record audio from microphone."""
    print(f"Recording for {duration} seconds...")
    
    # Play start sound
    subprocess.run(["afplay", "/System/Library/Sounds/Tink.aiff"], check=False)
    
    # Initialize PyAudio
    p = pyaudio.PyAudio()
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    temp_filename = temp_file.name
    temp_file.close()
    
    # Set up recording parameters
    chunk = 1024
    format = pyaudio.paInt16
    channels = 1
    rate = 16000
    
    # Open stream and record
    stream = p.open(
        format=format,
        channels=channels,
        rate=rate,
        input=True,
        frames_per_buffer=chunk
    )
    
    frames = []
    for _ in range(0, int(rate / chunk * duration)):
        data = stream.read(chunk)
        frames.append(data)
        
    # Close and clean up
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    # Save the recording
    wf = wave.open(temp_filename, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(p.get_sample_size(format))
    wf.setframerate(rate)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    # Play stop sound
    subprocess.run(["afplay", "/System/Library/Sounds/Basso.aiff"], check=False)
    
    return temp_filename

def main():
    """Run the simplified dictation program."""
    print("Ultra Simple Dictation Tool")
    print("==========================")
    print("Press Enter to start recording, Ctrl+C to exit")
    
    # Load whisper model (only once)
    print("Loading Whisper model...")
    model = whisper.load_model("tiny")
    
    try:
        while True:
            input("Press Enter to start recording...")
            
            # Record audio
            audio_file = record_audio(duration=5)
            
            # Transcribe audio
            print("Transcribing...")
            result = model.transcribe(audio_file)
            text = result["text"].strip()
            print(f"Transcribed: '{text}'")
            
            # Type the text
            if len(text) > 1:
                process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
                process.communicate(text.encode('utf-8'))
                time.sleep(0.2)
                pyautogui.hotkey('command', 'v')
                print("Text typed.")
            
            # Clean up
            os.remove(audio_file)
            
    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    main()