# Troubleshooting Guide: TurtleBot3 Simulation & Nav2 Autonomous Navigation

This guide documents the root cause analysis, diagnostic commands, and verified solutions for the common issues encountered when bringing up the TurtleBot3 simulation and Nav2 stack on Ubuntu 22.04 LTS (ROS 2 Humble, Gazebo Classic 11.10.2).

---

## 1. Issue: Gazebo `gzserver` Hangs or Exits with Code 255

### Symptoms
- When running `ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py`, Gazebo server hangs or terminates with exit code 255.
- `spawn_entity.py` logs `Waiting for service /spawn_entity, timeout = 30` and eventually dies with:
  ```text
  [ERROR] [spawn_entity.py]: Service /spawn_entity unavailable. Was Gazebo started with GazeboRosFactory?
  ```
- Gazebo log (`~/.gazebo/server-11345/default.log`) displays:
  ```text
  [Wrn] [ModelDatabase.cc:340] Getting models from[http://models.gazebosim.org/]. This may take a few seconds.
  ```

### Root Cause
Gazebo Classic defaults to querying `http://models.gazebosim.org` whenever a world references models that are not found in the immediate search path, or during initial database synchronization. The OSRF model database at `models.gazebosim.org` has been discontinued/migrated, causing HTTP request timeouts and indefinite synchronous hangs inside `ModelDatabase.cc`. While Gazebo is blocked waiting on network sockets, ROS 2 plugins (`libgazebo_ros_init.so` and `libgazebo_ros_factory.so`) cannot complete their initialization, and the `/spawn_entity` service is never advertised.

### Fix
1. Explicitly disable the remote database lookup by exporting an empty database URI:
   ```bash
   export GAZEBO_MODEL_DATABASE_URI=""
   ```
2. Ensure all required models (`ground_plane`, `sun`, `turtlebot3_burger`, `turtlebot3_world`) are available locally in `GAZEBO_MODEL_PATH`:
   ```bash
   export GAZEBO_MODEL_PATH=/usr/share/gazebo-11/models:/opt/ros/humble/share/turtlebot3_gazebo/models:${GAZEBO_MODEL_PATH}
   ```
Both environment variables are automatically configured in `src/start_robot.py` and `launch/simulation.launch.py`.

---

## 2. Issue: Robot Falls Through the Floor (Z = -10,000m)

### Symptoms
- Gazebo loads, but running `ros2 run tf2_ros tf2_echo odom base_link` shows:
  ```text
  - Translation: [-2.000, -0.500, -10896.746]
  ```
- The robot is falling through the ground plane into an empty void.

### Root Cause
If `GAZEBO_MODEL_PATH` is overridden with only `/opt/ros/humble/share/turtlebot3_gazebo/models` without prepending `/usr/share/gazebo-11/models`, Gazebo cannot find `model://ground_plane`. In the absence of a physics ground plane collision surface, gravity accelerates the robot downward continuously.

### Fix
Always include `/usr/share/gazebo-11/models` in `GAZEBO_MODEL_PATH`:
```bash
export GAZEBO_MODEL_PATH=/usr/share/gazebo-11/models:/opt/ros/humble/share/turtlebot3_gazebo/models:${GAZEBO_MODEL_PATH}
```
With the ground plane present, `tf2_echo odom base_link` confirms stable rest at `Z = 0.019m`.

---

## 3. Issue: Nav2 Transform Timeout (`Timed out waiting for transform from base_link to odom`)

### Symptoms
- When launching Nav2, RViz2 and terminal output show:
  ```text
  Timed out waiting for transform from base_link to odom
  Invalid frame ID "odom" passed to canTransform
  ```
- `/odom` and `/scan` are being published, but costmaps remain empty.

### Root Cause
Clock mismatch. Gazebo publishes simulation time on `/clock`. If Nav2 or RViz2 are launched with `use_sim_time:=false` (which is often the default in ROS 2 nodes), Nav2 evaluates TF timestamps against system wall-clock time (e.g. `1.79e9 s`) instead of Gazebo simulation time (e.g. `25.0 s`). Because the difference exceeds the transform tolerance, all lookups fail.

### Fix
Always set `use_sim_time:=true` for all Nav2 nodes and RViz2:
```bash
ros2 launch turtlebot3_autonomous_navigation navigation.launch.py use_sim_time:=true
```
In `config/nav2_params.yaml`, `use_sim_time: True` has been pre-configured across all lifecycle nodes.

---

## 4. Issue: AMCL Waits Indefinitely for Initial Pose

### Symptoms
- Nav2 starts, but navigation goals fail or the robot does not move.
- AMCL does not publish `map -> odom` transform.

### Root Cause
By default, AMCL requires an operator to set a "2D Pose Estimate" in RViz2 before it initializes particle filters.

### Fix
Configure initial pose coordinates directly in `config/nav2_params.yaml`:
```yaml
amcl:
  ros__parameters:
    use_sim_time: True
    set_initial_pose: true
    initial_pose:
      x: -2.0
      y: -0.5
      z: 0.01
      yaw: 0.0
```
This aligns the initial particle filter precisely with the spawn position `(-2.0, -0.5)` in `turtlebot3_world`, enabling fully autonomous startup.

---

## 5. Issue: Stale Gazebo Background Processes

### Symptoms
- Launching Gazebo fails with "Address already in use" or multiple masters competing on port 11345.

### Fix
Kill any lingering instances:
```bash
killall -9 gzserver gzclient
```
The launcher `src/start_robot.py` automatically checks for and terminates stale instances before booting.
