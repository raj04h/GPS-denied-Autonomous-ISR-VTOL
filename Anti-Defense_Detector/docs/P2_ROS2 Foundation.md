# Phase 2 — ROS2 Application Layer & Package Foundation

## Objective

Establish and validate the ROS 2 Humble robotics middleware and development environment on the validated NVIDIA Jetson Orin NX 16GB.

The objective was to install ROS 2, verify the middleware, establish persistent ROS environment configuration, create the project workspace, and validate basic ROS 2 node-to-node communication.

## Dataflow

```text
Ubuntu Laptop
     │
     │ USB Ethernet + SSH
     ▼
Jetson Orin NX 16GB
     │
     ▼
Ubuntu 22.04.5 LTS
     │
     ▼
ROS 2 Humble
     │
     ├── ROS 2 Nodes
     │
     ├── RMW Fast DDS
     │
     └── ROS 2 Topics
             │
             ▼
        Publisher → Subscriber
             │
             ▼
       /chatter communication
```

The Jetson provides the ROS 2 runtime environment. The laptop remains the remote development and control interface.

## Procedure

### 1. Verify the ROS 2 target platform

On the Jetson:

```bash
cat /etc/os-release
uname -m
```

The system was confirmed as Ubuntu 22.04.5 LTS on `aarch64`, matching the ROS 2 Humble target environment.

---

### 2. Install ROS 2 repository prerequisites

```bash
sudo apt install -y software-properties-common curl gnupg lsb-release
```

The required packages were already installed or were available through the configured Ubuntu repositories.

---

### 3. Install the ROS 2 repository key

```bash
sudo curl -fsSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
-o /usr/share/keyrings/ros-archive-keyring.gpg
```

The ROS repository key was successfully installed.

---

### 4. Add the ROS 2 repository

```bash
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
| sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
```

The repository was configured for Ubuntu `jammy`.

---

### 5. Update package indexes

```bash
sudo apt update
```

The ROS 2 repository was successfully reached and ARM64 packages were retrieved.

---

### 6. Install ROS 2 Humble base

```bash
sudo apt install -y ros-humble-ros-base
```

ROS 2 Humble base was successfully installed.

---

### 7. Load the ROS 2 environment

```bash
source /opt/ros/humble/setup.bash
```

Verify:

```bash
echo $ROS_DISTRO
```

Expected and verified:

```text
humble
```

---

### 8. Verify the ROS 2 installation

```bash
ros2 doctor --report
```

The ROS 2 installation was reported as:

```text
ROS 2 distribution: humble
Distribution status: active
Middleware: rmw_fastrtps_cpp
Platform: Linux aarch64
```

The installed ROS 2 packages included the base runtime, TF2, rosbag2, sensor messages, navigation messages and standard ROS 2 client libraries.

---

### 9. Install ROS 2 demonstration nodes

The initial attempt to run the ROS 2 publisher failed because the demonstration package was not installed:

```text
Package 'demo_nodes_cpp' not found
```

The missing package was installed:

```bash
sudo apt install -y ros-humble-demo-nodes-cpp
```

---

### 10. Validate ROS 2 publisher

Run:

```bash
ros2 run demo_nodes_cpp talker
```

The publisher successfully produced messages such as:

```text
Publishing: 'Hello World: 1'
```

---

### 11. Validate ROS 2 subscriber

From a separate SSH session:

```bash
ros2 run demo_nodes_cpp listener
```

The subscriber successfully received messages such as:

```text
I heard: [Hello World: 245]
I heard: [Hello World: 252]
```

This verified ROS 2 publisher/subscriber communication on the Jetson.

---

### 12. Persist the ROS 2 environment

Add ROS 2 to the shell startup environment:

```bash
echo 'source /opt/ros/humble/setup.bash' >> ~/.bashrc
```

Reload:

```bash
source ~/.bashrc
```

Verify:

```bash
echo $ROS_DISTRO
```

Result:

```text
humble
```

A new SSH session was also verified with the ROS 2 environment available.

---

### 13. Install ROS 2 development tools

```bash
sudo apt install -y \
python3-colcon-common-extensions \
python3-rosdep \
python3-vcstool \
git \
build-essential
```

The required ROS 2 workspace and development tools were installed.

---

### 14. Initialize rosdep

```bash
sudo rosdep init
rosdep update
```

`rosdep update` completed successfully and the ROS dependency database was populated.

---

### 15. Create the project workspace

```bash
mkdir -p ~/Autonomous-ISR-VTOL/src
cd ~/Autonomous-ISR-VTOL
```

The ROS 2 project workspace was created at:

```text
~/Autonomous-ISR-VTOL
```

---

### 16. Build the workspace

```bash
colcon build
```

Result:

```text
Summary: 0 packages finished
```

The build completed successfully. No project packages existed in the workspace yet, so no package compilation was expected.

---

### 17. Persist the project workspace environment

```bash
echo 'source ~/Autonomous-ISR-VTOL/install/setup.bash' >> ~/.bashrc
```

The workspace environment was configured for subsequent shells.

## Configuration

| Component | Verified Configuration |
|---|---|
| OS | Ubuntu 22.04.5 LTS |
| Architecture | aarch64 |
| ROS Distribution | ROS 2 Humble |
| ROS Middleware | `rmw_fastrtps_cpp` |
| ROS Base | `ros-humble-ros-base` |
| Demo Package | `ros-humble-demo-nodes-cpp` |
| Dependency Tool | `rosdep` |
| Build Tool | `colcon` |
| Version Control | Git |
| C/C++ Build Tools | `build-essential` |
| Project Workspace | `~/Autonomous-ISR-VTOL` |
| Source Directory | `~/Autonomous-ISR-VTOL/src` |
| ROS Environment | `/opt/ros/humble/setup.bash` |

## Validation

### ROS 2 Installation

Verified:

```text
ROS 2 Humble
Distribution status: active
```

### ROS 2 Middleware

Verified:

```text
rmw_fastrtps_cpp
```

### ROS 2 Publisher

Verified `demo_nodes_cpp` talker successfully publishing messages.

### ROS 2 Subscriber

Verified `demo_nodes_cpp` listener successfully receiving messages.

### ROS 2 Communication

Publisher/subscriber communication was successfully validated on the Jetson.

### Persistent Environment

Verified:

```bash
echo $ROS_DISTRO
```

Result:

```text
humble
```

after establishing a new SSH session.

### Development Workspace

Verified:

```text
~/Autonomous-ISR-VTOL
```

with successful `colcon build`.

## Result

**PASS**

The ROS 2 foundation is operational and validated.

The following were successfully established:

- ROS 2 Humble
- ROS 2 repository
- ROS 2 base runtime
- ROS environment
- Persistent ROS environment
- ROS 2 middleware
- ROS 2 publisher
- ROS 2 subscriber
- ROS 2 node communication
- `rosdep`
- `colcon`
- Git
- C/C++ build tools
- ROS 2 project workspace
- Workspace build

## Problems & Limitations

- The first attempt to run `demo_nodes_cpp` failed because the demonstration package was not installed. The package was subsequently installed and validated.
- A new SSH session initially did not have the ROS 2 environment loaded until the persistent `.bashrc` configuration was added.
- The workspace currently contains no project-specific ROS 2 packages; therefore the successful `colcon build` did not compile application code.
- No flight controller, camera, IMU or other UAV hardware interface was integrated during this phase.
- No VIO, SLAM, perception, planning or autonomous flight functionality was implemented or validated.

## Summary

ROS 2 Humble has been successfully installed and validated on the Jetson Orin NX 16GB.

The ROS 2 runtime, middleware, development tools, dependency management, workspace and basic publisher/subscriber communication are operational. The Jetson is now ready for project-specific ROS 2 development and hardware-interface integration.

## Next Step

Proceed to **Phase 3 — Hardware Interface Foundation** and begin verification of the available UAV hardware interfaces, starting with device detection, communication paths, ROS 2 interface requirements and timestamp/frame conventions.