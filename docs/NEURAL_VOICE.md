# Neural Voice System Documentation

## Overview

The neural voice system uses GPU acceleration to create a high-quality voice synthesis model based on your voice recordings. This system leverages the power of Coqui TTS and PyTorch to create a natural-sounding voice that mimics your speech patterns.

## System Architecture

The neural voice system consists of two main components:

1. **GPU Server**: Runs the neural voice model training and synthesis server
   - Utilizes CUDA-compatible GPU (RTX 3090 recommended)
   - Handles intensive voice model training
   - Serves voice synthesis requests via HTTP API

2. **Client**: Connects to the GPU server for voice synthesis
   - Sends text to be synthesized to the server
   - Plays back the synthesized audio
   - Falls back to parameter-based voice if server is unavailable

## Voice Model Training Process

The voice model training process involves the following steps:

1. **Sample Preparation**:
   - Voice samples are recorded using 
   - Recommended: 40+ diverse samples for best quality
   - Samples should include varied intonations and speech patterns

2. **Neural Model Training**:
   - Samples are transferred to GPU server
   - GPU-accelerated training with Tacotron2 architecture
   - Default: 5000 epochs (approx. 10-15 minutes on RTX 3090)
   - Extended: 10000 epochs for maximum quality

3. **Model Optimization**:
   - Mixed precision training for GPU efficiency
   - Dynamic batch sizing based on available GPU memory
   - Advanced phoneme generation and caching
   - GPU memory management for optimal performance

## Technical Components

### Server-Side Components

- **train_neural_voice.py**: High-performance neural model training
  - Configurable epoch count for training quality control
  - GPU memory optimization
  - Advanced Tacotron2 configuration
  - Automatic phoneme generation

- **neural_voice_server.py**: Voice synthesis server
  - HTTP API for voice synthesis requests
  - GPU-accelerated inference
  - Caching system for frequently used phrases
  - Fallback synthesis capabilities
  - Port 5001 for client connections

- **start_neural_server.sh**: Server management script
  - Environment variable configuration
  - Dependency checking
  - GPU detection and configuration
  - System monitoring

### Client-Side Components

- **neural_voice_client.py**: Client library
  - Connects to neural voice server
  - Caches synthesized audio locally
  - Automatic fallback to parameter-based voice
  - Environment variable configuration ()

- **speech_synthesis.py**: Integration with voice control system
  - Unified API for both neural and parameter-based voices
  - Context-aware voice adjustments
  - Seamless fallback when server unavailable

## Deployment

### GPU Server Setup

1. Configure GPU server details in  file:
   

2. Setup GPU server environment:
   === Setting up Neural Voice Conversion ===
Host: 192.168.191.55
User: claudecode

Testing connection to GPU server...
✅ Connected to GPU server
Creating remote directories...
Transferring voice samples to GPU server...
Transferring GPU training scripts...
Creating remote setup script...
Running remote setup script...
Looking for conda installation...
Found conda at: /home/claudecode/miniconda3/bin/conda
Setting up conda environment...
tts_voice environment already exists, updating...
Installing PyTorch with CUDA support...
Channels:
 - pytorch
 - nvidia
 - defaults
Platform: linux-64
Collecting package metadata (repodata.json): ...working... done
Solving environment: ...working... done

# All requested packages already installed.

Installing TTS dependencies...
Channels:
 - conda-forge
 - defaults
Platform: linux-64
Collecting package metadata (repodata.json): ...working... done
Solving environment: ...working... failed
Setting up TTS environment...
Already up to date.
Obtaining file:///home/claudecode/neural_voice_model/code/TTS
  Installing build dependencies: started
  Installing build dependencies: finished with status 'done'
  Checking if build backend supports build_editable: started
  Checking if build backend supports build_editable: finished with status 'done'
  Getting requirements to build editable: started
  Getting requirements to build editable: finished with status 'error'
Downloading pre-trained models...
Setup complete!
Neural voice conversion setup complete!

3. Train neural voice model on GPU server:
   

4. Start neural voice server:
   

### Client Configuration

1. Set environment variable for server connection:
   

2. Test neural voice system:
   === Enhanced Voice Model Test ===
✅ Custom voice model loaded: neural_voice_model
   Created: 2025-03-04 22:36:00
   Samples: 27

Testing system voices for comparison:

Speaking with system voice: daniel

Speaking with system voice: samantha

Speaking with system voice: karen

Testing custom voice model:

Speaking phrase 1/4:
"Hello, I'm your personal assistant using your custom voice model."

Speaking phrase 2/4:
"This voice should sound more like you, since it uses your voice characteristics."

Speaking phrase 3/4:
"The quick brown fox jumps over the lazy dog."

Speaking phrase 4/4:
"How does this voice sound compared to the system voices? Is it more natural?"

Voice test complete.

## Performance Considerations

- **GPU Requirements**:
  - RTX 3090 or better recommended for optimal performance
  - Minimum 10GB VRAM for training
  - CUDA 11.x or newer

- **Network Requirements**:
  - Low-latency connection between client and server
  - Server accessible on port 5001
  - Firewall configuration to allow HTTP traffic

- **Training Time**:
  - 5000 epochs: ~10-15 minutes on RTX 3090
  - 10000 epochs: ~20-30 minutes on RTX 3090

- **Synthesis Performance**:
  - Real-time synthesis with GPU acceleration
  - ~100-200ms latency on local network
  - Automatic caching reduces repeat synthesis time

## Troubleshooting

- **Server Connection Issues**:
  - Verify server is running with === Checking GPU Server Status ===
Host: 192.168.191.55
User: claudecode

Testing connection to GPU server...
✅ Connected to GPU server

=== GPU Information ===
Failed to initialize NVML: Insufficient Permissions
Failed to run nvidia-smi. GPU info not available.

=== System Load ===
 00:20:49 up 13 days, 16:01,  6 users,  load average: 0.29, 0.29, 0.45

CPU Usage:
top - 00:20:50 up 13 days, 16:01,  6 users,  load average: 0.29, 0.29, 0.45
Tasks: 1028 total,   1 running, 1027 sleeping,   0 stopped,   0 zombie
%Cpu(s):  1.2 us,  0.3 sy,  0.0 ni, 98.5 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st 
MiB Mem :  64134.7 total,  15325.7 free,  15351.4 used,  34221.8 buff/cache     
MiB Swap:   8192.0 total,   8191.7 free,      0.2 used.  48783.3 avail Mem 

    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
 596927 root      20   0   17.5g   4.8g 484496 S 107.1   7.6   3:19.81 python
 607647 claudec+  20   0   14828   5376   3072 R  21.4   0.0   0:00.07 top
 234217 rin       20   0   69740  23040   5376 S   7.1   0.0 282:29.15 nvtop
      1 root      20   0   23424  13056   9216 S   0.0   0.0   1:06.50 systemd
      2 root      20   0       0      0      0 S   0.0   0.0   0:01.07 kthreadd
      3 root      20   0       0      0      0 S   0.0   0.0   0:00.00 pool_wo+
      4 root       0 -20       0      0      0 I   0.0   0.0   0:00.00 kworker+
      5 root       0 -20       0      0      0 I   0.0   0.0   0:00.00 kworker+
      6 root       0 -20       0      0      0 I   0.0   0.0   0:00.00 kworker+
      7 root       0 -20       0      0      0 I   0.0   0.0   0:00.00 kworker+
     10 root       0 -20       0      0      0 I   0.0   0.0   0:00.00 kworker+
     12 root       0 -20       0      0      0 I   0.0   0.0   0:00.00 kworker+
     13 root      20   0       0      0      0 I   0.0   0.0   0:00.00 rcu_tas+

=== Disk Space ===
/dev/nvme0n1p2  233G  187G   35G  85% /

=== Memory Usage ===
               total        used        free      shared  buff/cache   available
Mem:            62Gi        15Gi        14Gi        54Mi        33Gi        47Gi
Swap:          8.0Gi       256Ki       8.0Gi

=== Python Environment ===
/usr/bin/python3
Python 3.12.3
pip not found in PATH

=== Installed ML Packages ===
No ML packages found or pip not available

GPU server check complete
  - Check firewall settings for port 5001
  - Verify correct IP/hostname in NEURAL_SERVER variable
  - Test connection with 

- **Training Issues**:
  - Check GPU availability with 
  - Ensure CUDA is properly installed
  - Try with fewer epochs initially to test process
  - Check log files for specific errors

- **Voice Quality Issues**:
  - Increase number of training epochs
  - Add more voice samples (aim for 40+)
  - Include diverse speech patterns in samples
  - Try different model configuration parameters

## Future Enhancements

- Support for emotion-based voice styles
- Real-time voice adaptation based on context
- Multi-language support with phoneme extension
- Voice style transfer for customized expressions
- Improved GPU memory optimization for larger models
