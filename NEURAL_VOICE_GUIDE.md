# GPU-Accelerated Neural Voice Training Guide

This guide will help you train a high-quality neural voice model using the RTX 3090 GPU server for voice cloning.

## Prerequisites

1. Access to GPU server with RTX 3090 or better
2. At least 20 voice samples (40+ recommended for best quality)
3. CUDA libraries installed on GPU server
4. Configured .env file with GPU server credentials

## Step 1: Set Up Neural Voice Environment

First, set up the neural voice environment on the GPU server:

\\=== Setting up Neural Voice Conversion ===
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

## Package Plan ##

  environment location: /home/claudecode/miniconda3/envs/tts_voice

  added / updated specs:
    - cudatoolkit=11.8
    - pytorch==2.0.1
    - torchaudio==2.0.2
    - torchvision==0.15.2


The following packages will be downloaded:

    package                    |            build
    ---------------------------|-----------------
    blas-1.0                   |         openblas          46 KB
    libprotobuf-3.20.3         |       he621ea3_0         2.4 MB
    mysql-8.4.0                |       h0bac5ae_0        56.6 MB
    ninja-1.12.1               |       h06a4308_0           8 KB
    ninja-base-1.12.1          |       hdb19cb5_0         157 KB
    pytorch-2.0.1              |cpu_py38hab5cca8_0        56.9 MB
    ------------------------------------------------------------
                                           Total:       116.0 MB

The following NEW packages will be INSTALLED:

  blas               pkgs/main/linux-64::blas-1.0-openblas 
  cuda-cudart        nvidia/linux-64::cuda-cudart-11.8.89-0 
  cuda-cupti         nvidia/linux-64::cuda-cupti-11.8.87-0 
  cuda-libraries     nvidia/linux-64::cuda-libraries-11.8.0-0 
  cuda-nvrtc         nvidia/linux-64::cuda-nvrtc-11.8.89-0 
  cuda-nvtx          nvidia/linux-64::cuda-nvtx-11.8.86-0 
  cuda-runtime       nvidia/linux-64::cuda-runtime-11.8.0-0 
  cudatoolkit        pkgs/main/linux-64::cudatoolkit-11.8.0-h6a678d5_0 
  libcublas          nvidia/linux-64::libcublas-11.11.3.6-0 
  libcufft           nvidia/linux-64::libcufft-10.9.0.58-0 
  libcufile          nvidia/linux-64::libcufile-1.9.1.3-0 
  libcurand          nvidia/linux-64::libcurand-10.3.5.147-0 
  libcusolver        nvidia/linux-64::libcusolver-11.4.1.48-0 
  libcusparse        nvidia/linux-64::libcusparse-11.7.5.86-0 
  libnpp             nvidia/linux-64::libnpp-11.8.0.86-0 
  libnvjpeg          nvidia/linux-64::libnvjpeg-11.9.0.86-0 
  ninja              pkgs/main/linux-64::ninja-1.12.1-h06a4308_0 
  ninja-base         pkgs/main/linux-64::ninja-base-1.12.1-hdb19cb5_0 
  pytorch            pkgs/main/linux-64::pytorch-2.0.1-cpu_py38hab5cca8_0 
  pytorch-cuda       pytorch/linux-64::pytorch-cuda-11.8-h7e8668a_6 
  pytorch-mutex      pytorch/noarch::pytorch-mutex-1.0-cuda 
  torchvision        pytorch/linux-64::torchvision-0.15.2-py38_cu118 

The following packages will be REMOVED:

  fsspec-2025.2.0-pypi_0
  nvidia-cublas-cu12-12.1.3.1-pypi_0
  nvidia-cuda-cupti-cu12-12.1.105-pypi_0
  nvidia-cuda-nvrtc-cu12-12.1.105-pypi_0
  nvidia-cuda-runtime-cu12-12.1.105-pypi_0
  nvidia-cudnn-cu12-9.1.0.70-pypi_0
  nvidia-cufft-cu12-11.0.2.54-pypi_0
  nvidia-curand-cu12-10.3.2.106-pypi_0
  nvidia-cusolver-cu12-11.4.5.107-pypi_0
  nvidia-cusparse-cu12-12.1.0.106-pypi_0
  nvidia-nccl-cu12-2.20.5-pypi_0
  nvidia-nvjitlink-cu12-12.8.61-pypi_0
  nvidia-nvtx-cu12-12.1.105-pypi_0
  torch-2.4.1-pypi_0

The following packages will be SUPERSEDED by a higher-priority channel:

  torchaudio             pypi/pypi::torchaudio-2.4.1-pypi_0 --> pytorch/linux-64::torchaudio-2.0.2-py38_cu118 

The following packages will be DOWNGRADED:

  libprotobuf                             4.25.3-he621ea3_0 --> 3.20.3-he621ea3_0 
  mysql                                    8.4.0-h29a9f33_1 --> 8.4.0-h0bac5ae_0 



Downloading and Extracting Packages: ...working...pytorch-2.0.1        | 56.9 MB   |            |   0% 
mysql-8.4.0          | 56.6 MB   |            |   0% [A

libprotobuf-3.20.3   | 2.4 MB    |            |   0% [A[A


ninja-base-1.12.1    | 157 KB    |            |   0% [A[A[A



blas-1.0             | 46 KB     |            |   0% [A[A[A[A




ninja-1.12.1         | 8 KB      |            |   0% [A[A[A[A[A



blas-1.0             | 46 KB     | ########## | 100% [A[A[A[A

libprotobuf-3.20.3   | 2.4 MB    | 6          |   7% [A[A


ninja-base-1.12.1    | 157 KB    | #####1     |  51% [A[A[A



blas-1.0             | 46 KB     | ########## | 100% [A[A[A[A




ninja-1.12.1         | 8 KB      | ########## | 100% [A[A[A[A[A




ninja-1.12.1         | 8 KB      | ########## | 100% [A[A[A[A[A




ninja-1.12.1         | 8 KB      | ########## | 100% [A[A[A[A[A


ninja-base-1.12.1    | 157 KB    | ########## | 100% [A[A[A


ninja-base-1.12.1    | 157 KB    | ########## | 100% [A[A[A

libprotobuf-3.20.3   | 2.4 MB    | ########## | 100% [A[A
mysql-8.4.0          | 56.6 MB   |            |   0% [A

libprotobuf-3.20.3   | 2.4 MB    | ########## | 100% [A[A

libprotobuf-3.20.3   | 2.4 MB    | ########## | 100% [A[A
mysql-8.4.0          | 56.6 MB   | 3          |   3% [Apytorch-2.0.1        | 56.9 MB   |            |   0% pytorch-2.0.1        | 56.9 MB   |            |   0% 
mysql-8.4.0          | 56.6 MB   | 5          |   6% [Apytorch-2.0.1        | 56.9 MB   |            |   1% 
mysql-8.4.0          | 56.6 MB   | 8          |   9% [A
mysql-8.4.0          | 56.6 MB   | #3         |  14% [Apytorch-2.0.1        | 56.9 MB   | 1          |   1% pytorch-2.0.1        | 56.9 MB   | 2          |   3% 
mysql-8.4.0          | 56.6 MB   | #6         |  17% [Apytorch-2.0.1        | 56.9 MB   | 4          |   4% 
mysql-8.4.0          | 56.6 MB   | #9         |  20% [Apytorch-2.0.1        | 56.9 MB   | 6          |   7% 
mysql-8.4.0          | 56.6 MB   | ##2        |  22% [Apytorch-2.0.1        | 56.9 MB   | 9          |   9% 
mysql-8.4.0          | 56.6 MB   | ##5        |  25% [Apytorch-2.0.1        | 56.9 MB   | #1         |  12% 
mysql-8.4.0          | 56.6 MB   | ##8        |  28% [Apytorch-2.0.1        | 56.9 MB   | #7         |  18% pytorch-2.0.1        | 56.9 MB   | ##2        |  23% 
mysql-8.4.0          | 56.6 MB   | ###1       |  31% [Apytorch-2.0.1        | 56.9 MB   | ##6        |  26% 
mysql-8.4.0          | 56.6 MB   | ###3       |  33% [Apytorch-2.0.1        | 56.9 MB   | ###2       |  33% 
mysql-8.4.0          | 56.6 MB   | ###5       |  35% [Apytorch-2.0.1        | 56.9 MB   | ###6       |  36% 
mysql-8.4.0          | 56.6 MB   | ###7       |  37% [Apytorch-2.0.1        | 56.9 MB   | ####3      |  43% 
mysql-8.4.0          | 56.6 MB   | ###9       |  39% [A
mysql-8.4.0          | 56.6 MB   | ####       |  41% [Apytorch-2.0.1        | 56.9 MB   | ####7      |  48% 
mysql-8.4.0          | 56.6 MB   | ####2      |  42% [Apytorch-2.0.1        | 56.9 MB   | #####1     |  52% 
mysql-8.4.0          | 56.6 MB   | ####3      |  44% [Apytorch-2.0.1        | 56.9 MB   | #####6     |  57% pytorch-2.0.1        | 56.9 MB   | ######     |  61% 
mysql-8.4.0          | 56.6 MB   | ####5      |  45% [Apytorch-2.0.1        | 56.9 MB   | ######5    |  65% 
mysql-8.4.0          | 56.6 MB   | ####6      |  47% [Apytorch-2.0.1        | 56.9 MB   | ######8    |  69% 
mysql-8.4.0          | 56.6 MB   | ####7      |  48% [Apytorch-2.0.1        | 56.9 MB   | #######4   |  75% pytorch-2.0.1        | 56.9 MB   | #######9   |  79% 
mysql-8.4.0          | 56.6 MB   | ####8      |  49% [Apytorch-2.0.1        | 56.9 MB   | ########3  |  83% 
mysql-8.4.0          | 56.6 MB   | ####9      |  50% [Apytorch-2.0.1        | 56.9 MB   | ########7  |  87% 
mysql-8.4.0          | 56.6 MB   | #####      |  51% [Apytorch-2.0.1        | 56.9 MB   | #########3 |  93% 
mysql-8.4.0          | 56.6 MB   | #####1     |  52% [Apytorch-2.0.1        | 56.9 MB   | #########7 |  97% 
mysql-8.4.0          | 56.6 MB   | #####2     |  53% [Apytorch-2.0.1        | 56.9 MB   | ########## | 100% 
mysql-8.4.0          | 56.6 MB   | #####3     |  53% [A
mysql-8.4.0          | 56.6 MB   | #####4     |  55% [A
mysql-8.4.0          | 56.6 MB   | #####6     |  56% [A
mysql-8.4.0          | 56.6 MB   | #####7     |  58% [A
mysql-8.4.0          | 56.6 MB   | #####9     |  60% [A
mysql-8.4.0          | 56.6 MB   | ######2    |  62% [A
mysql-8.4.0          | 56.6 MB   | ######5    |  66% [A
mysql-8.4.0          | 56.6 MB   | ######8    |  68% [A
mysql-8.4.0          | 56.6 MB   | #######2   |  72% [A
mysql-8.4.0          | 56.6 MB   | #######5   |  75% [A
mysql-8.4.0          | 56.6 MB   | #######7   |  78% [A
mysql-8.4.0          | 56.6 MB   | ########3  |  83% [A
mysql-8.4.0          | 56.6 MB   | ########6  |  87% [A
mysql-8.4.0          | 56.6 MB   | ########9  |  90% [A
mysql-8.4.0          | 56.6 MB   | #########4 |  94% [A
mysql-8.4.0          | 56.6 MB   | #########7 |  97% [A
mysql-8.4.0          | 56.6 MB   | ########## | 100% [A
mysql-8.4.0          | 56.6 MB   | ########## | 100% [Apytorch-2.0.1        | 56.9 MB   | ########## | 100%                                                      
                                                     [A

                                                     [A[A


                                                     [A[A[A



                                                     [A[A[A[A




                                                     [A[A[A[A[A done
Preparing transaction: - \ | done
Verifying transaction: - \ | / - \ | / - \ | / - \ | / - \ | / - \ | / - \ | / - \ | / done
Executing transaction: \ | / - \ | / - \ | / - \ | / - \ | / - \ | / By downloading and using the CUDA Toolkit conda packages, you accept the terms and conditions of the CUDA End User License Agreement (EULA): https://docs.nvidia.com/cuda/eula/index.html

- \ | done
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
Neural voice conversion setup complete!\

This will:
- Transfer your voice samples to the GPU server
- Set up a Python environment with PyTorch, Coqui TTS, and other dependencies
- Transfer the high-performance training scripts

## Step 2: Train the Neural Voice Model

To train a high-performance neural voice model with full GPU utilization:

1. Connect to your GPU server via SSH
2. Navigate to neural_voice_model/code directory
3. Run the training script with increased epochs:

\\\

The training process will:
- Utilize the full RTX 3090 GPU capacity
- Train for approximately 10-15 minutes
- Use advanced techniques including:
  - Mixed precision training
  - Optimized batch size based on available memory
  - Dynamic learning rate scheduling
  - Advanced audio processing parameters

## Step 3: Start the Neural Voice Server

After training, start the neural voice server to provide TTS services:

\\\

The server will:
- Run on port 5001, accessible from other machines
- Utilize GPU acceleration for real-time voice synthesis
- Provide fallback capabilities if needed

## Step 4: Connect from Local Machine

On your local machine, set the NEURAL_SERVER environment variable:

\\=== Enhanced Voice Model Test ===
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

Voice test complete.\

## Advanced Configuration

### Improving Voice Quality

For even better voice quality:
- Record 40+ diverse samples in a quiet environment
- Include various intonations and speech patterns
- Increase training epochs to 10000 for extended training

### Server Performance

The neural voice server includes:
- Automatic caching for frequently used phrases
- GPU memory optimization
- Graceful fallback to parameter-based voice if neural model unavailable

## Troubleshooting

If you encounter issues:

1. Check GPU server connection with:
   \\=== Checking GPU Server Status ===
Host: 192.168.191.55
User: claudecode

Testing connection to GPU server...
✅ Connected to GPU server

=== GPU Information ===
Failed to initialize NVML: Insufficient Permissions
Failed to run nvidia-smi. GPU info not available.

=== System Load ===
 00:16:39 up 13 days, 15:57,  6 users,  load average: 0.47, 0.44, 0.55

CPU Usage:
top - 00:16:39 up 13 days, 15:57,  6 users,  load average: 0.47, 0.44, 0.55
Tasks: 1037 total,   1 running, 1036 sleeping,   0 stopped,   0 zombie
%Cpu(s):  0.1 us,  0.3 sy,  0.0 ni, 99.6 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st 
MiB Mem :  64134.7 total,  15523.4 free,  15154.2 used,  34221.3 buff/cache     
MiB Swap:   8192.0 total,   8191.7 free,      0.2 used.  48980.5 avail Mem 

    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
 606951 claudec+  20   0   14828   5376   3072 R  21.4   0.0   0:00.07 top
      1 root      20   0   23424  13056   9216 S   0.0   0.0   1:06.35 systemd
      2 root      20   0       0      0      0 S   0.0   0.0   0:01.07 kthreadd
      3 root      20   0       0      0      0 S   0.0   0.0   0:00.00 pool_wo+
      4 root       0 -20       0      0      0 I   0.0   0.0   0:00.00 kworker+
      5 root       0 -20       0      0      0 I   0.0   0.0   0:00.00 kworker+
      6 root       0 -20       0      0      0 I   0.0   0.0   0:00.00 kworker+
      7 root       0 -20       0      0      0 I   0.0   0.0   0:00.00 kworker+
     10 root       0 -20       0      0      0 I   0.0   0.0   0:00.00 kworker+
     12 root       0 -20       0      0      0 I   0.0   0.0   0:00.00 kworker+
     13 root      20   0       0      0      0 I   0.0   0.0   0:00.00 rcu_tas+
     14 root      20   0       0      0      0 I   0.0   0.0   0:00.00 rcu_tas+
     15 root      20   0       0      0      0 I   0.0   0.0   0:00.00 rcu_tas+

=== Disk Space ===
/dev/nvme0n1p2  233G  187G   35G  85% /

=== Memory Usage ===
               total        used        free      shared  buff/cache   available
Mem:            62Gi        14Gi        15Gi        54Mi        33Gi        47Gi
Swap:          8.0Gi       256Ki       8.0Gi

=== Python Environment ===
/usr/bin/python3
Python 3.12.3
pip not found in PATH

=== Installed ML Packages ===
No ML packages found or pip not available

GPU server check complete\

2. Verify neural server is running:
   \\\

3. If training fails, try with fewer epochs initially:
   \\\

4. For server connection issues, check firewall settings and ensure port 5001 is accessible
