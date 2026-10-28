#!/usr/bin/env python3
"""
TurtleBot3 Simulation & Navigation Lifecycle Launcher
Robust startup, readiness monitoring, dependency validation, and clean shutdown.
"""

import argparse
import atexit
import os
import signal
import subprocess
import sys
import time

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROS_SETUP = "/opt/ros/humble/setup.bash"

# Track spawned subprocesses for clean shutdown
active_processes = []

def cleanup():
    """Terminate all active child processes and lingering simulator processes."""
    print("\n[INFO] Shutting down simulation and child processes...")
    for proc in active_processes:
        if proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                pass
    time.sleep(1.5)
    for proc in active_processes:
        if proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                pass
    # Clean lingering Gazebo and Nav2 processes
    subprocess.run(["pkill", "-9", "-f", "component_container|gzserver|gzclient|robot_state_publisher"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run("rm -f /dev/shm/fastrtps_* /dev/shm/sem.fastrtps_*", shell=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("[INFO] Cleanup complete. Shutdown successful.")

atexit.register(cleanup)

def handle_sigint(signum, frame):
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, handle_sigint)
signal.signal(signal.SIGTERM, handle_sigint)

def check_dependencies():
    """Verify that ROS 2 Humble and required simulation packages are installed."""
    print("[1/4] Verifying system dependencies & environment...")

    if not os.path.exists(ROS_SETUP):
        print(f"[ERROR] ROS 2 Humble setup file not found at {ROS_SETUP}")
        sys.exit(1)

    required_cmds = ["ros2", "gzserver", "gazebo", "rviz2"]
    for cmd in required_cmds:
        res = subprocess.run(f"source {ROS_SETUP} && which {cmd}",
                             shell=True, executable="/bin/bash",
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0:
            print(f"[ERROR] Required binary '{cmd}' not found in PATH.")
            sys.exit(1)

    required_pkgs = ["turtlebot3_gazebo", "turtlebot3_navigation2", "nav2_bringup", "gazebo_ros"]
    for pkg in required_pkgs:
        res = subprocess.run(f"source {ROS_SETUP} && ros2 pkg prefix {pkg}",
                             shell=True, executable="/bin/bash",
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0:
            print(f"[ERROR] Required ROS 2 package '{pkg}' is missing.")
            sys.exit(1)

    print("  -> System dependencies validated.")

def configure_environment():
    """Set critical environment variables to prevent Gazebo hang and robot fall-through."""
    print("[2/4] Configuring Gazebo and Robot environment...")
    env = os.environ.copy()

    # Crucial: disable obsolete remote model database that causes gzserver hang/exit code 255
    env["GAZEBO_MODEL_DATABASE_URI"] = ""
    env["TURTLEBOT3_MODEL"] = "burger"

    # Crucial: include ground_plane, sun, and turtlebot3 models
    tb3_models = "/opt/ros/humble/share/turtlebot3_gazebo/models"
    gz_models = "/usr/share/gazebo-11/models"
    project_models = os.path.join(PROJECT_DIR, "models")
    
    current_model_path = env.get("GAZEBO_MODEL_PATH", "")
    paths = [gz_models, tb3_models, project_models]
    if current_model_path:
        paths.append(current_model_path)
    env["GAZEBO_MODEL_PATH"] = ":".join([p for p in paths if os.path.exists(p)])

    print(f"  -> TURTLEBOT3_MODEL={env['TURTLEBOT3_MODEL']}")
    print(f"  -> GAZEBO_MODEL_PATH={env['GAZEBO_MODEL_PATH']}")
    print(f"  -> GAZEBO_MODEL_DATABASE_URI=\"\" (remote lookup disabled)")
    return env

def kill_stale_processes():
    """Ensure no stale simulator processes exist from previous runs."""
    res = subprocess.run(["pgrep", "-f", "gzserver|gzclient|nav2|rviz2|component_container"],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.stdout:
        print("  -> Terminating existing Gazebo/Nav2 instances...")
        subprocess.run(["pkill", "-9", "-f", "gzserver|gzclient|rviz2|component_container"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.0)
    # Clean up orphaned Fast-DDS shared memory locks that cause RTPS_TRANSPORT_SHM errors
    subprocess.run("rm -f /dev/shm/fastrtps_* /dev/shm/sem.fastrtps_*", shell=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def wait_for_topic(topic_name, timeout_sec=30, env=None):
    """Wait until a specific ROS 2 topic is active and publishing."""
    start = time.time()
    cmd = f"source {ROS_SETUP} && ros2 topic list"
    while time.time() - start < timeout_sec:
        res = subprocess.run(cmd, shell=True, executable="/bin/bash",
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True)
        if topic_name in res.stdout.split():
            return True
        time.sleep(1.0)
    return False

def verify_simulation_readiness(env, timeout_sec=45):
    """Confirm robot spawn, sensor data, and odometry publishing."""
    print("[4/4] Verifying simulation readiness...")
    essential_topics = ["/clock", "/odom", "/scan", "/tf"]

    for topic in essential_topics:
        sys.stdout.write(f"  -> Checking topic {topic} ... ")
        sys.stdout.flush()
        if wait_for_topic(topic, timeout_sec=timeout_sec, env=env):
            print("ACTIVE")
        else:
            print("TIMED OUT")
            print(f"[ERROR] Essential topic {topic} did not become active within {timeout_sec}s.")
            return False

    # Check that robot odometry has non-null data and stable pose
    cmd = f"source {ROS_SETUP} && timeout 5 ros2 topic echo /odom --once"
    res = subprocess.run(cmd, shell=True, executable="/bin/bash",
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True)
    if "position:" in res.stdout:
        print("  -> Robot odometry and transform stream confirmed valid.")
        return True
    else:
        print("[WARNING] Could not sample single odometry message.")
        return False

def main():
    parser = argparse.ArgumentParser(description="TurtleBot3 Simulation & Navigation Launcher")
    parser.add_argument("--headless", action="store_true", help="Run Gazebo in headless mode (no GUI)")
    parser.add_argument("--with-nav", action="store_true", help="Also start Nav2 stack & RViz2")
    parser.add_argument("--no-rviz", action="store_true", help="Disable RViz2 when --with-nav is used")
    args = parser.parse_args()

    check_dependencies()
    kill_stale_processes()
    env = configure_environment()

    print("[3/4] Launching TurtleBot3 simulation...")
    sim_launch = os.path.join(PROJECT_DIR, "launch", "simulation.launch.py")
    gui_arg = "false" if args.headless else "true"
    sim_cmd = f"source {ROS_SETUP} && ros2 launch {sim_launch} gui:={gui_arg}"

    sim_proc = subprocess.Popen(
        sim_cmd, shell=True, executable="/bin/bash", env=env,
        preexec_fn=os.setsid
    )
    active_processes.append(sim_proc)

    # Monitor simulation readiness
    if not verify_simulation_readiness(env, timeout_sec=45):
        print("[ERROR] Simulation startup verification failed. Terminating.")
        cleanup()
        sys.exit(1)

    print("\n" + "="*60)
    print(" TURTLEBOT3 SIMULATION READY")
    print(" Active Robot: Burger")
    print(" Simulator:    Gazebo Classic 11.10.2")
    print(" Environment:  TurtleBot3 House World")
    print(" Topics:       /clock, /odom, /scan, /cmd_vel, /tf")
    print("="*60 + "\n")

    nav_proc = None
    if args.with_nav:
        print("[+] Launching Nav2 stack and RViz2...")
        nav_launch = os.path.join(PROJECT_DIR, "launch", "navigation.launch.py")
        rviz_arg = "false" if args.no_rviz else "true"
        nav_cmd = f"source {ROS_SETUP} && ros2 launch {nav_launch} use_rviz:={rviz_arg} use_sim_time:=true"
        nav_proc = subprocess.Popen(
            nav_cmd, shell=True, executable="/bin/bash", env=env,
            preexec_fn=os.setsid
        )
        active_processes.append(nav_proc)
        print("  -> Nav2 bringup initiated. Waiting for lifecycle nodes...")
        time.sleep(5.0)

    print("\n[READY] System is running. Press Ctrl+C to stop simulation safely.\n")

    try:
        while True:
            time.sleep(1.0)
            if sim_proc.poll() is not None:
                print(f"[ERROR] Gazebo simulation terminated unexpectedly with code {sim_proc.returncode}")
                break
            if nav_proc and nav_proc.poll() is not None:
                print(f"[ERROR] Nav2 process terminated unexpectedly with code {nav_proc.returncode}")
                break
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()

if __name__ == "__main__":
    main()
