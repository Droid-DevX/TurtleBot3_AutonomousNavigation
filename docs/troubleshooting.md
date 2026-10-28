# Troubleshooting Guide: TurtleBot3 Simulation & Nav2 Autonomous Navigation

This guide documents the root cause analysis, diagnostic commands, and verified solutions for the common issues encountered when bringing up the TurtleBot3 simulation and Nav2 stack on Ubuntu 22.04 LTS (ROS 2 Humble, Gazebo Classic 11.10.2).

---

## 1. Issue: Gazebo `gzserver` Hangs or Exits with Code 255

### Symptoms
- When running `ros2 launch turtlebot3_autonomous_navigation simulation.launch.py`, Gazebo server hangs or terminates with exit code 255.
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
2. Ensure all required models (`ground_plane`, `sun`, `turtlebot3_burger`, `turtlebot3_house`) are available locally in `GAZEBO_MODEL_PATH`:
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
      y: 1.0
      z: 0.01
      yaw: 0.0
```
This aligns the initial particle filter precisely with the safe spawn position `(-2.0, 1.0)` in the `turtlebot3_house` Living Room, enabling fully autonomous startup.

---

## 5. Issue: Invalid Frame ID `${namespace}base_link` and Dropped Laser Scans

### Symptoms
- Nav2 local costmap repeatedly reports `Invalid frame ID "base_link" ... frame does not exist` when requesting the transform from `base_link` to `odom`.
- AMCL and RViz2 drop `base_scan` messages because the transform from `base_scan` to `odom`/`map` cannot be resolved.
- Echoing `/tf_static` shows frame IDs with literal `${namespace}` prefixes (`${namespace}base_footprint`, `${namespace}base_link`, `${namespace}base_scan`).

### Root Cause
In ROS 2 Humble, the URDF file in `turtlebot3_description` uses xacro macros with `$(arg namespace)`. If loaded raw using `open().read()` rather than through xacro evaluation or `turtlebot3_gazebo`'s resolved URDF, `robot_state_publisher` publishes literal string names with `${namespace}`. Because Gazebo's differential drive plugin publishes `odom -> base_footprint` without prefixes, the robot transform chain is broken.

### Fix
In `launch/simulation.launch.py`, load the canonical, resolved URDF from `turtlebot3_gazebo`:
```python
tb3_model = os.environ.get('TURTLEBOT3_MODEL', 'burger')
urdf_path = os.path.join(
    get_package_share_directory('turtlebot3_gazebo'),
    'urdf',
    f'turtlebot3_{tb3_model}.urdf'
)
```
This restores the proper transform tree:
`map -> odom -> base_footprint -> base_link -> base_scan`.

---

## 6. Issue: Stale Background Processes & Fast-DDS Shared-Memory Collisions

### Symptoms
- Launching Gazebo fails with "Address already in use" on port 11345.
- Fast-DDS logs `[RTPS_TRANSPORT_SHM Error] Failed init_port fastrtps_port7425` or `Failed create_port`.
- Nav2 nodes fail to load into `nav2_container`, and `navigation_demo.py` remains waiting at `Waiting for Nav2 stack lifecycle nodes to activate...`.
- `ros2 lifecycle get /amcl` reports `Node not found`.

### Root Cause
If Gazebo Classic, `component_container_isolated`, or `rviz2` are terminated abruptly (e.g. via `kill -9` without a graceful shutdown), orphaned Fast-DDS mutex locks (`/dev/shm/fastrtps_*` and `/dev/shm/sem.fastrtps_*`) remain unlinked in shared memory. Subsequent launches attempt to allocate already-claimed shared memory ports, preventing intra-process communication between Nav2 lifecycle components.

### Fix
1. Terminate all lingering simulator and container processes:
   ```bash
   pkill -9 -f "gzserver|gzclient|component_container|robot_state_publisher|rviz2" || true
   ```
2. Unlink orphaned Fast-DDS shared memory and semaphore files:
   ```bash
   rm -f /dev/shm/fastrtps_* /dev/shm/sem.fastrtps_*
   ```
3. Relaunch the stack using `src/start_robot.py --with-nav`. The launcher automatically executes these cleanup steps before starting child nodes.

