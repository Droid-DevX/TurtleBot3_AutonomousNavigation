# TurtleBot3 Autonomous Navigation in ROS 2 Humble

[![ROS 2](https://img.shields.io/badge/ROS%202-Humble-22314E.svg?logo=ros)](https://docs.ros.org/en/humble/)
[![Gazebo](https://img.shields.io/badge/Simulator-Gazebo%20Classic%2011-FF6600.svg)](http://gazebosim.org/)
[![Nav2](https://img.shields.io/badge/Navigation-Nav2-blue.svg)](https://navigation.ros.org/)
[![Robot](https://img.shields.io/badge/Robot-TurtleBot3%20Burger-yellow.svg)](https://emanual.robotis.com/docs/en/platform/turtlebot3/overview/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

Autonomous mobile robot (AMR) navigation demonstration using the **TurtleBot3 Burger**, **ROS 2 Humble**, **Gazebo Classic 11**, and the **Nav2** stack in the multi-room **TurtleBot3 House World** (`turtlebot3_house.world`).

<p align="center">
  <img src="docs/images/gazebo_simulation.png" alt="Gazebo House Simulation" width="49%"/>
  <img src="docs/images/rviz_visualization.png" alt="RViz2 Navigation Visualization" width="49%"/>
</p>

---

## 1. Project Title and Overview

This project implements an end-to-end autonomous navigation and dynamic obstacle avoidance pipeline for a differential-drive robot operating within an indoor residential environment.

The system demonstrates:
- Simulated physical environment bringup with verified collision geometry and simulated sensors.
- Map-based localization using Adaptive Monte Carlo Localization (AMCL).
- Global path planning and collision-free local trajectory generation using the Nav2 stack.
- Programmatic multi-waypoint mission execution using a standalone Python controller that commands goals, tracks distance telemetry, and handles task completion.

---

## 2. Features

- **House World Simulation**: Operates inside the canonical TurtleBot3 House environment featuring partitions, interior doorways, furniture, and narrow corridors.
- **TurtleBot3 Burger Robot**: Differential-drive mobile base equipped with a 360° 2D LiDAR scanner (LDS-01) and wheel encoders.
- **Autonomous AMCL Localization**: Pre-configured initial pose estimation (`-2.0, 1.0, 0.0`) in the Living Room base with particle filter convergence.
- **Global Path Planning**: Global planning using `NavfnPlanner` with the A* search algorithm for optimal, oscillation-free path generation.
- **Local Motion Control & Obstacle Avoidance**: Dynamic Window Approach (DWB Local Planner) executing real-time obstacle avoidance.
- **Multi-Waypoint Python Demonstration**: Programmatic mission manager built with `nav2_simple_commander.BasicNavigator` that sequences multi-room waypoints and outputs live progress metrics.
- **RViz2 Visualization**: Pre-configured display configuration visualizing sensor streams, costmaps, planner paths, and robot transforms.

---

## 3. Technology Stack

| Component | Technology | Version / Specification |
|---|---|---|
| **Operating System** | Ubuntu Linux | 22.04 LTS (Jammy Jellyfish) |
| **Robotics Middleware** | ROS 2 | Humble Hawksbill |
| **Physics Simulator** | Gazebo Classic | 11.10.2 |
| **Navigation Stack** | Nav2 | ROS 2 Humble Nav2 Stack |
| **Localization** | AMCL | `nav2_amcl` (Differential Motion Model) |
| **Motion Controller** | DWB Local Planner | `dwb_core::DWBLocalPlanner` |
| **Global Planner** | Navfn (A*) | `nav2_navfn_planner/NavfnPlanner` |
| **Robot Platform** | TurtleBot3 Burger | Differential drive, 2D LiDAR, wheel odometry |
| **Programming Language** | Python | Python 3.10 |

---

## 4. Repository Structure

```text
TurtleBot3/
├── README.md               # Complete project documentation and run guide
├── package.xml             # ROS 2 package manifest (ament_python)
├── setup.py                # Python package installer and entry point definitions
├── setup.cfg               # Installation script configuration
├── requirements.txt        # Optional Python dependencies
├── .gitignore              # Git ignore rules for ROS 2 and Python artifacts
├── config/
│   ├── nav2_params.yaml    # Tuned Nav2 stack configuration (costmaps, AMCL, planners)
│   └── rviz_config.rviz    # Pre-configured RViz2 visualization setup
├── docs/
│   └── troubleshooting.md  # Detailed root cause analysis and troubleshooting guide
├── launch/
│   ├── bringup.launch.py   # Full system launch (Gazebo + Nav2 + RViz2)
│   ├── navigation.launch.py# Nav2 stack and RViz2 bringup
│   └── simulation.launch.py# Gazebo Classic and robot state publisher bringup
├── maps/
│   ├── map.pgm             # 2D occupancy grid map of TurtleBot3 House (16m x 12m)
│   └── map.yaml            # Map metadata (resolution: 0.05 m/cell, origin: [-8.0, -6.0])
├── resource/
│   └── turtlebot3_autonomous_navigation  # Package marker file
├── scripts/
│   └── verify_setup.sh     # System pre-flight verifier script
├── src/
│   ├── navigation_demo.py  # Standalone multi-waypoint navigation client script
│   └── start_robot.py      # Automated simulation launcher with process management
└── worlds/
    └── turtlebot3_house.world # Gazebo world file for the TurtleBot3 House
```

### File Purposes

- **`src/start_robot.py`**: Boots the simulation, verifies dependencies, clears stale process locks, sets up required environment variables, and launches Gazebo and Nav2.
- **`src/navigation_demo.py`**: Connects to the Nav2 action servers, sets initial AMCL pose, validates node readiness, and navigates through the three target rooms.
- **`launch/simulation.launch.py`**: Loads the house world into Gazebo Classic, resolves the canonical URDF model, and launches `robot_state_publisher` and `spawn_entity.py`.
- **`launch/navigation.launch.py`**: Initializes the Nav2 lifecycle manager, costmaps, planners, controllers, and RViz2.
- **`config/nav2_params.yaml`**: Contains parameter tuning for all 9 Nav2 lifecycle nodes, sensor topics, costmap inflation, and tolerances.
- **`maps/map.yaml` & `maps/map.pgm`**: The physical occupancy grid corresponding to the interior walls and obstacles of the house world.
- **`scripts/verify_setup.sh`**: Runs non-destructive sanity checks verifying that ROS 2, Gazebo, and the required packages are properly installed.

---

## 5. Prerequisites and Dependencies

### System Requirements
- Ubuntu 22.04 LTS (x86_64).
- ROS 2 Humble Desktop installation (`/opt/ros/humble`).
- Gazebo Classic 11 (`gazebo-11`).

### Required ROS 2 Packages (Apt)
The following binary packages must be installed on your system:
```bash
sudo apt update && sudo apt install -y \
  ros-humble-turtlebot3-gazebo \
  ros-humble-turtlebot3-navigation2 \
  ros-humble-nav2-bringup \
  ros-humble-nav2-simple-commander \
  ros-humble-gazebo-ros \
  ros-humble-robot-state-publisher \
  ros-humble-rviz2 \
  python3-transforms3d
```

### Repository-Contained Assets
The following assets are provided directly within this repository and do **not** need external downloading:
- World model (`worlds/turtlebot3_house.world`).
- House occupancy grid (`maps/map.yaml` and `maps/map.pgm`).
- Tailored Nav2 parameter configuration (`config/nav2_params.yaml`).
- Saved RViz visualization template (`config/rviz_config.rviz`).

---

## 6. Installation and Setup

### 1. Clone the Repository
Clone the repository to your local workspace:
```bash
cd <workspace_directory>
git clone <repository_url>
cd <repository_directory>
```

### 2. Configure Environment Variables
Add the ROS 2 setup and robot model to your current shell session:
```bash
source /opt/ros/humble/setup.bash
export TURTLEBOT3_MODEL=burger
```

To ensure Gazebo Classic does not hang trying to query the discontinued online model database, disable remote database queries:
```bash
export GAZEBO_MODEL_DATABASE_URI=""
```
*(Note: `src/start_robot.py` and `launch/simulation.launch.py` automatically set this for you when launched.)*

### 3. Ensure Executable Permissions
Make scripts and launch files executable:
```bash
chmod +x scripts/verify_setup.sh src/start_robot.py src/navigation_demo.py launch/*.py
```

### 4. Verify System Setup
Run the included verification script to confirm that all tools and models are discovered:
```bash
./scripts/verify_setup.sh
```
Expected output:
```text
============================================================
 TurtleBot3 Autonomous Navigation Environment Verifier
============================================================
[PASS] ROS 2 Humble installation found at /opt/ros/humble
[PASS] TURTLEBOT3_MODEL is set to burger
[PASS] Gazebo simulator detected: Gazebo multi-robot simulator, version 11.10.2
[PASS] ROS 2 package 'turtlebot3_gazebo' is available
[PASS] ROS 2 package 'turtlebot3_navigation2' is available
[PASS] ROS 2 package 'nav2_bringup' is available
[PASS] ROS 2 package 'gazebo_ros' is available
[PASS] ROS 2 package 'nav2_simple_commander' is available
[PASS] Local Gazebo model assets verified (ground_plane, turtlebot3_burger)
============================================================
 ALL SYSTEM PRE-CHECKS PASSED SUCCESSFULLY
============================================================
```

---

## 7. How to Run

Running the demonstration requires **two separate terminals**:
- **Terminal 1**: Runs the Gazebo physics simulation, robot spawn, and Nav2 navigation stack.
- **Terminal 2**: Runs the Python autonomous navigation client script.

> **Warning**: Do not launch `start_robot.py` multiple times simultaneously. Running duplicate simulations causes Fast-DDS shared memory port collisions and prevents Nav2 nodes from loading.

### Terminal 1: Launch Simulation & Navigation Stack

Open your first terminal and run:
```bash
cd <path_to_repository>
source /opt/ros/humble/setup.bash
export TURTLEBOT3_MODEL=burger
./src/start_robot.py --with-nav
```

**What this command does:**
1. Verifies system dependencies and local Gazebo models.
2. Clears any stale Gazebo/Nav2 processes or DDS shared memory locks.
3. Launches Gazebo Classic with `worlds/turtlebot3_house.world`.
4. Spawns the TurtleBot3 Burger at initial coordinates `(x: -2.0, y: 1.0, yaw: 0.0)`.
5. Starts `robot_state_publisher` and publishes the complete coordinate transform tree.
6. Boots the Nav2 navigation stack (costmaps, AMCL, planners, controllers) and opens RViz2.

Wait approximately 10–15 seconds until Terminal 1 displays:
```text
[READY] System is running. Press Ctrl+C to stop simulation safely.
```

---

### Terminal 2: Run Autonomous Navigation Demo

Once Terminal 1 is ready, open a second terminal and execute:
```bash
cd <path_to_repository>
source /opt/ros/humble/setup.bash
export TURTLEBOT3_MODEL=burger
python3 src/navigation_demo.py
```

**What this command does:**
1. Connects to the simulated clock `/clock` and Nav2 action servers.
2. Initializes the robot's pose in AMCL and waits for particle filter convergence.
3. Sequentially navigates through all three house waypoints.
4. Prints live distance-to-goal and elapsed time telemetry.
5. Displays a final validation summary table.

---

### How to Stop Safely
- In Terminal 2, `navigation_demo.py` exits automatically once the demonstration is complete.
- In Terminal 1, press **`Ctrl+C`** to trigger the cleanup sequence in `start_robot.py`, which cleanly terminates all background Gazebo, Nav2, and RViz2 processes.

---

## 8. Navigation Waypoints

<p align="center">
  <img src="docs/images/navigation_trajectory.gif" alt="Autonomous Navigation Trajectory Animation" width="75%"/>
  <br/>
  <em>Figure: Autonomous multi-room navigation sequence across the TurtleBot3 House floorplan.</em>
</p>

The mission script (`src/navigation_demo.py`) sequences three waypoints traversing the different rooms of the house:

| Goal # | Target Name | X (m) | Y (m) | Yaw (deg) | Description |
|---|---|---|---|---|---|
| **Waypoint 1** | **North-East Master Room** | `4.50` | `2.50` | `0.0°` | Traverses through the living room doorway into the master bedroom. |
| **Waypoint 2** | **South-East Sunroom** | `6.00` | `-1.00` | `-90.0°` | Navigates through the connecting hallway into the sunroom lounge. |
| **Waypoint 3** | **Return to Living Room Base** | `-2.00` | `1.00` | `180.0°` | Returns across the entire house to the home docking position. |

Each waypoint has a configured timeout (90s–120s). The client monitors progress feedback, prints distance remaining, and records whether Nav2 reported `SUCCEEDED`.

---

## 9. RViz Visualization

The simulation bringup automatically launches RViz2 loaded with [`config/rviz_config.rviz`](config/rviz_config.rviz).

<p align="center">
  <img src="docs/images/rviz_visualization.png" alt="RViz2 Navigation Stack Displays" width="85%"/>
  <br/>
  <em>Figure: Real-time Nav2 displays showing 2D costmap inflation, LiDAR scan returns, global plan, and AMCL particle cloud.</em>
</p>

### Key Displays
- **RobotModel**: Displays the 3D visual mesh of the TurtleBot3 Burger.
- **TF (`/tf`, `/tf_static`)**: Displays coordinate frames (`map -> odom -> base_footprint -> base_link -> base_scan`).
- **Map (`/map`)**: Shows the static 2D occupancy grid loaded from `maps/map.yaml`.
- **LaserScan (`/scan`)**: Real-time laser scan beams (red points) reflecting off walls and furniture.
- **Particle Cloud (`/particle_cloud`)**: Green particle cloud showing AMCL's probabilistic localization distribution.
- **Global Costmap (`/global_costmap/costmap`)**: Inflated obstacle costs used for long-range path planning.
- **Local Costmap (`/local_costmap/costmap`)**: High-frequency dynamic costmap used for local reactive avoidance.
- **Global Plan**: Green path line representing the A* path generated by `planner_server`.
- **Local Trajectory**: Smooth trajectory evaluated by the DWB controller driving the wheels.

---

## 10. Expected Results

When running the two-terminal setup, the expected execution flow is:

### Terminal 1 Bringup Log:
```text
============================================================
 TURTLEBOT3 SIMULATION & NAVIGATION BRINGUP
============================================================
[1/4] Verifying system dependencies & environment...
  -> System dependencies validated.
[2/4] Configuring Gazebo and Robot environment...
  -> TURTLEBOT3_MODEL=burger
  -> GAZEBO_MODEL_PATH=/usr/share/gazebo-11/models:...
  -> GAZEBO_MODEL_DATABASE_URI="" (remote lookup disabled)
[3/4] Launching Gazebo Classic simulation (turtlebot3_house.world)...
  -> Simulation process launched (PID: xxxxx).
  -> Waiting for Gazebo /clock and /odom topics...
  -> Gazebo physics engine active and publishing clock.
[4/4] Launching Nav2 Navigation Stack...
  -> Navigation stack and RViz2 launched (PID: xxxxx).
  -> Waiting for navigation nodes to transition to active...
  -> All 9 Nav2 lifecycle nodes active.

[READY] System is running. Press Ctrl+C to stop simulation safely.
```

### Terminal 2 Demonstration Results:
```text
============================================================
 TURTLEBOT3 AUTONOMOUS NAVIGATION DEMONSTRATOR
============================================================
[INFO] Synchronizing with simulation clock...
  -> Simulation clock active (current sim time: 394.00s).
[1/4] Setting initial pose: x=-2.0, y=1.0, yaw=0.0°
[2/4] Waiting for Nav2 stack lifecycle nodes to activate...
  -> Nav2 is fully active and ready.
[INFO] Confirming AMCL laser scan localization convergence...
  -> AMCL localization active and ready.
[3/4] Executing autonomous navigation sequence (3 goals)...

--- Navigating to Waypoint 1 (North-East Master Room): x=4.50, y=2.50 ---
  [SUCCESS] Reached Waypoint 1 (North-East Master Room) in 39.1s!

--- Navigating to Waypoint 2 (South-East Sunroom): x=6.00, y=-1.00 ---
  [SUCCESS] Reached Waypoint 2 (South-East Sunroom) in 18.7s!

--- Navigating to Waypoint 3 (Return to Living Room Base): x=-2.00, y=1.00 ---
  [SUCCESS] Reached Waypoint 3 (Return to Living Room Base) in 48.1s!

============================================================
 NAVIGATION DEMO SUMMARY RESULTS
============================================================
 - Waypoint 1 (North-East Master Room)     : [PASS] (39.1s)
 - Waypoint 2 (South-East Sunroom)         : [PASS] (18.7s)
 - Waypoint 3 (Return to Living Room Base) : [PASS] (48.1s)
============================================================
[DEMO COMPLETE] All navigation goals succeeded with obstacle avoidance!
```

*(Note: Execution durations are approximate and depend on hardware simulation real-time factor.)*

---

## 11. Troubleshooting

For comprehensive root-cause analyses, refer to the [Troubleshooting Guide](docs/troubleshooting.md). Below are the most common issues and solutions:

### 1. Gazebo Server Hangs or Fails with Code 255
- **Cause**: Gazebo Classic attempts to connect to `models.gazebosim.org` over HTTP.
- **Fix**: Run `export GAZEBO_MODEL_DATABASE_URI=""` prior to launching.

### 2. Demo Stuck at "Waiting for Nav2 stack lifecycle nodes to activate..."
- **Cause**: An earlier background instance of Gazebo or Nav2 is still running, locking Fast-DDS shared memory ports (`/dev/shm/fastrtps_*`).
- **Fix**: Terminate all lingering processes and clear shared memory:
  ```bash
  pkill -9 -f "gzserver|gzclient|component_container" || true
  rm -f /dev/shm/fastrtps_* /dev/shm/sem.fastrtps_*
  ```
  Then restart `start_robot.py`.

### 3. Transform / TF Lookup Extrapolation Errors
- **Cause**: System wall clock time is being used instead of Gazebo simulation time.
- **Fix**: Ensure `use_sim_time:=true` is passed to all ROS 2 launch commands and verified in `nav2_params.yaml`.

### 4. Basic Diagnostic Commands
Use these commands in a separate terminal to inspect stack health:
```bash
# Check active simulation clock
ros2 topic echo /clock --once

# Inspect all active lifecycle nodes
ros2 node list

# Query individual lifecycle state
ros2 lifecycle get /amcl
ros2 lifecycle get /bt_navigator

# Check transform between odometry and robot base
ros2 run tf2_ros tf2_echo odom base_link
```

---

## 12. Demonstration and Submission

When preparing demonstration artifacts for review or assignment submission:
- **Demonstration Video**: Record the running demonstration displaying the Gazebo window, RViz2 visualization, and the terminal output side-by-side.
- **Key Milestones to Show**:
  1. Initial pose alignment in the Living Room base.
  2. Trajectory planning and doorway traversal to Waypoint 1 (Master Bedroom).
  3. Narrow corridor obstacle avoidance to Waypoint 2 (Sunroom).
  4. Return journey to Waypoint 3 (Living Room base).
  5. The final `[DEMO COMPLETE]` terminal summary.
- **Repository Cleanliness**: Per standard practices, recorded video files (`.mp4`, `.webm`, `.gif`) are excluded from the git repository via `.gitignore` and should be submitted or hosted externally.

---

## 13. Limitations

- **Simulation Scope**: This project is built and verified within a Gazebo Classic physics simulation environment. Physical robot hardware deployment would require motor controller drivers, hardware LiDAR calibration, and wheel slippage compensation.
- **Deterministic Map Dependency**: Navigation relies on a pre-built static occupancy grid map (`map.yaml`). Operating in previously unmapped environments would require dynamic SLAM integration (`slam_toolbox` or `cartographer`).
- **Heuristic Path Planning**: Uses classical geometric planning (Navfn + DWB) rather than machine-learning or reinforcement-learning policies.

---

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](package.xml) section for details.
