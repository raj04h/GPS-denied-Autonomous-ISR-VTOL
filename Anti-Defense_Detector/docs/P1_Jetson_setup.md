# Phase 1 — Jetson Foundation

## Objective

Establish and validate the NVIDIA Jetson Orin NX 16GB as the onboard edge-compute platform for the autonomous UAV software stack.

The objective was to bring up the Jetson with a known-good operating system and GPU-compute environment, verify storage and hardware operation, and establish reliable headless control from the Ubuntu laptop without requiring an HDMI/display connection.

## Dataflow

```text
Ubuntu Laptop
     │
     │ USB cable
     ▼
USB Ethernet Network
192.168.55.100
     │
     │ SSH
     ▼
Jetson Orin NX 16GB
192.168.55.1
     │
     ├── Jetson Linux / Ubuntu
     ├── NVMe Storage
     └── NVIDIA GPU
             │
             ▼
        CUDA 12.6
```

The laptop provides the development and remote-control interface. The Jetson provides the onboard compute environment.

## Procedure

### 1. Identify the Jetson hardware

After connecting the Jetson to the Ubuntu laptop, verify the USB device:

```bash
lsusb
```

During recovery mode, the Jetson was detected as:

```text
0955:7323 NVIDIA Corp. APX
```

This identified the target as an NVIDIA Jetson Orin NX platform.

---

### 2. Enter Jetson USB recovery mode

With the Jetson powered off:

- Connect the USB-C cable between the Jetson and Ubuntu laptop.
- Short the J14 recovery pins:
  - Pin 9 — GND
  - Pin 10 — FORCE_RECOVERY
- Apply power to the Jetson.
- Release the recovery connection after the board enters recovery mode.

Verify the recovery device from the Ubuntu laptop:

```bash
lsusb
```

Expected recovery device:

```text
0955:7323 NVIDIA Corp. APX
```

---

### 3. Install NVIDIA SDK Manager on the Ubuntu laptop

The NVIDIA SDK Manager package was installed:

```text
sdkmanager_26.1.0-14392_amd64.deb
```

Verify the installed SDK Manager:

```bash
which sdkmanager
```

Expected:

```text
/usr/bin/sdkmanager
```

Verify the version:

```bash
sdkmanager --version
```

Expected version:

```text
26.1.0.14392
```

---

### 4. Flash Jetson Linux using NVIDIA SDK Manager

Launch SDK Manager:

```bash
sdkmanager
```

SDK Manager configuration used:

```text
Action:
    Install

Product:
    Jetson

Host:
    Ubuntu 22.04 x86_64

Target hardware:
    Jetson Orin NX modules

Target OS:
    Linux

JetPack:
    6.2.3

Installation method:
    Direct Flash

Storage:
    NVMe

Pre-Config:
    Username: hraj
```

No additional SDK packages such as DeepStream or Holoscan were selected.

The Jetson Linux image was flashed to:

```text
/dev/nvme0n1p1
```

SDK Manager reported the Jetson Linux flash as successful.

---

### 5. Verify normal Jetson boot

After flashing, verify that the Jetson is no longer in recovery mode:

```bash
lsusb
```

The normal Jetson USB device was detected as:

```text
0955:7020 NVIDIA Corp. L4T (Linux for Tegra) running on Tegra
```

Connect to the Jetson through SSH after normal boot.

---

### 6. Verify the Jetson operating system

On the Jetson:

```bash
cat /etc/os-release
```

Verify the kernel:

```bash
uname -a
```

Verify the CPU architecture:

```bash
uname -m
```

Verify the Jetson model:

```bash
cat /proc/device-tree/model
```

The validated baseline was:

```text
Ubuntu 22.04.5 LTS
Linux 5.15.199-tegra
aarch64
NVIDIA Jetson Orin NX Engineering Reference Developer Kit
```

---

### 7. Verify NVMe storage

Run:

```bash
lsblk
```

Then:

```bash
df -h /
```

The root filesystem was verified on:

```text
/dev/nvme0n1p1
```

with approximately:

```text
456 GB total
```

---

### 8. Establish USB Ethernet networking

On the Ubuntu laptop, identify the USB network interface:

```bash
ip addr
```

The Jetson USB network interface was configured with:

```text
Laptop:
192.168.55.100/24
```

The Jetson USB bridge was configured with:

```text
Jetson:
192.168.55.1/24
```

Verify connectivity from the laptop:

```bash
ping -c 3 192.168.55.1
```

Successful replies verified the laptop-to-Jetson USB network path.

---

### 9. Configure SSH access

From the Ubuntu laptop:

```bash
ssh hraj@192.168.55.1
```

Verify the Jetson shell is accessible.

An existing Ed25519 SSH key was verified on the laptop:

```bash
ls -la ~/.ssh/
```

The public key was already present on the Jetson. Verification with:

```bash
ssh-copy-id hraj@192.168.55.1
```

reported that the key already existed on the remote system.

---

### 10. Configure the `jetson` SSH host alias

Create/edit:

```bash
nano ~/.ssh/config
```

The following configuration was used:

```text
Host jetson
    HostName 192.168.55.1
    User hraj
    IdentityFile ~/.ssh/id_ed25519
```

Set the required permissions:

```bash
chmod 600 ~/.ssh/config
```

Verify the alias:

```bash
ssh jetson
```

---

### 11. Verify headless Jetson operation

From the laptop:

```bash
ssh jetson
```

Verify the remote system:

```bash
hostname
uname
uname -m
cat /proc/device-tree/model
```

The Jetson was successfully controlled through USB networking and SSH without an HDMI/display connection.

---

### 12. Verify CUDA compiler

Verify the CUDA compiler:

```bash
which nvcc
```

Expected:

```text
/usr/local/cuda-12.6/bin/nvcc
```

Then:

```bash
nvcc --version
```

The validated CUDA version was:

```text
CUDA 12.6
V12.6.68
```

---

### 13. Compile and execute a CUDA test

Create a temporary CUDA test program:

```bash
nano /tmp/cuda_test.cu
```

Compile it:

```bash
nvcc /tmp/cuda_test.cu -o /tmp/cuda_test
```

Execute:

```bash
/tmp/cuda_test
```

The test successfully detected:

```text
CUDA devices: 1
GPU: Orin
Compute capability: 8.7
```

The CUDA test was then removed:

```bash
rm -f /tmp/cuda_test /tmp/cuda_test.cu
```

---

### 14. Verify Jetson runtime health

Run:

```bash
tegrastats
```

Verify CPU, GPU, memory and temperature telemetry.

Stop the monitoring process with:

```text
Ctrl+C
```

The Jetson was observed operating normally at idle with no abnormal thermal or resource condition during the validation.

---

### 15. Final Jetson baseline verification

Verify the main platform information:

```bash
cat /etc/os-release
uname -a
uname -m
cat /proc/device-tree/model
df -h /
which nvcc
nvcc --version
```

The resulting validated platform baseline was:

```text
Jetson Orin NX 16GB
JetPack 6.2.3
Jetson Linux R36.5.2
Ubuntu 22.04.5 LTS
aarch64
CUDA 12.6
NVMe storage
USB Ethernet
SSH
Headless operation
```

## Configuration

| Component | Verified Configuration |
|---|---|
| Hardware | NVIDIA Jetson Orin NX Engineering Reference Developer Kit |
| Module | Jetson Orin NX 16GB |
| JetPack | 6.2.3 |
| Jetson Linux | R36.5.2 |
| Ubuntu | 22.04.5 LTS |
| Architecture | aarch64 |
| Kernel | 5.15.199-tegra |
| Storage | NVMe |
| Root filesystem | `/dev/nvme0n1p1` |
| NVMe capacity | ~456 GB |
| CUDA | 12.6 |
| `nvcc` | `/usr/local/cuda-12.6/bin/nvcc` |
| CUDA compute capability | 8.7 |
| USB network — laptop | `192.168.55.100/24` |
| USB network — Jetson | `192.168.55.1/24` |
| SSH host alias | `jetson` |
| Jetson user | `hraj` |

The Jetson was configured for headless operation through USB networking and SSH.

## Validation

### Jetson Operating System

Verified:

```text
Ubuntu 22.04.5 LTS
GNU/Linux 5.15.199-tegra aarch64
```

### Jetson Hardware

Verified:

```text
NVIDIA Jetson Orin NX Engineering Reference Developer Kit
```

### NVMe Storage

Verified the NVMe root filesystem was mounted and operational with approximately 456 GB total capacity.

### USB Networking

Verified the laptop-to-Jetson USB network:

```text
Laptop:  192.168.55.100
Jetson:  192.168.55.1
```

Connectivity was verified with successful ping responses.

### SSH

Verified remote access using:

```bash
ssh jetson
```

The Jetson could be controlled entirely from the Ubuntu laptop without an HDMI/display connection.

### CUDA

Verified:

```text
CUDA compilation tools, release 12.6
```

A CUDA test kernel was compiled and executed successfully.

The Jetson GPU was detected as:

```text
GPU: Orin
Compute Capability: 8.7
CUDA devices: 1
```

### Runtime Health

`tegrastats` was used to verify Jetson runtime health, including CPU/GPU utilization, memory and temperature readings.

## Result

**PASS**

The Jetson Orin NX 16GB foundation is operational and validated.

The following were successfully established:

- Jetson Linux installation
- JetPack 6.2.3
- Ubuntu 22.04.5 LTS
- NVMe-based system
- USB networking
- SSH remote control
- Headless operation
- CUDA 12.6
- CUDA compilation and execution
- Orin GPU detection
- GPU compute capability 8.7
- Basic system runtime validation

The Jetson is now established as the compute platform for the subsequent robotics and autonomy software stack.

## Problems & Limitations

- HDMI/display was not used; the system is operated headlessly through the laptop.
- Jetson Wi-Fi was investigated but not completed because the installed kernel did not provide the required Intel `iwlwifi` support. Wi-Fi configuration was therefore left aside.
- No external flight controller or camera was integrated during this phase.
- This phase validates the compute platform only; autonomy, perception, state estimation and flight-control functions were not implemented or validated.

## Summary

The Jetson Orin NX 16GB was successfully brought from initial hardware recovery through a known-good JetPack/Jetson Linux installation and validated as an operational edge-compute platform.

The system has verified storage, operating-system, CUDA/GPU and headless remote-development capability. The validated baseline provides the foundation for the subsequent ROS 2 and UAV hardware-interface phases.

## Next Step

Proceed to **Phase 2 — ROS 2 Foundation** and establish the robotics middleware, development environment, ROS 2 workspace and communication validation on the validated Jetson platform.