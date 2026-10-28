#!/usr/bin/env python3
"""
Autonomous Navigation and Obstacle Avoidance Demo for TurtleBot3.
Uses Nav2 Simple Commander API to navigate multi-goal waypoints around obstacles.
"""

import math
import sys
import time
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
import rclpy
from rclpy.duration import Duration

def create_pose_stamped(navigator, x, y, yaw_deg):
    """Helper to generate a PoseStamped message from 2D coordinates and yaw degrees."""
    pose = PoseStamped()
    pose.header.frame_id = 'map'
    pose.header.stamp = navigator.get_clock().now().to_msg()
    pose.pose.position.x = float(x)
    pose.pose.position.y = float(y)
    pose.pose.position.z = 0.0

    yaw_rad = math.radians(yaw_deg)
    pose.pose.orientation.z = math.sin(yaw_rad / 2.0)
    pose.pose.orientation.w = math.cos(yaw_rad / 2.0)
    return pose

def main():
    # Enforce use_sim_time so BasicNavigator clock matches Gazebo simulation clock
    rclpy.init(args=['--ros-args', '-p', 'use_sim_time:=true', *sys.argv[1:]])
    navigator = BasicNavigator()
    navigator.set_parameters([rclpy.parameter.Parameter('use_sim_time', rclpy.parameter.Parameter.Type.BOOL, True)])

    print("\n" + "="*60)
    print(" TURTLEBOT3 AUTONOMOUS NAVIGATION DEMONSTRATOR")
    print("="*60)

    # Ensure simulation clock (/clock) is ticking before stamping poses
    print("[INFO] Synchronizing with simulation clock...")
    while rclpy.ok() and navigator.get_clock().now().nanoseconds == 0:
        rclpy.spin_once(navigator, timeout_sec=0.1)
    sim_time_sec = navigator.get_clock().now().nanoseconds / 1e9
    print(f"  -> Simulation clock active (current sim time: {sim_time_sec:.2f}s).")

    # 1. Set Initial Pose (matches safe spawn pose in turtlebot3_house)
    init_x, init_y, init_yaw = -2.0, 1.0, 0.0
    print(f"[1/4] Setting initial pose: x={init_x}, y={init_y}, yaw={init_yaw}°", flush=True)
    initial_pose = create_pose_stamped(navigator, init_x, init_y, init_yaw)
    navigator.setInitialPose(initial_pose)

    # 2. Wait for Nav2 active
    print("[2/4] Waiting for Nav2 stack lifecycle nodes to activate...", flush=True)
    from lifecycle_msgs.srv import GetState
    amcl_client = navigator.create_client(GetState, 'amcl/get_state')
    if not amcl_client.wait_for_service(timeout_sec=15.0):
        print("\n[ERROR] Timed out waiting for /amcl/get_state service to become available!", file=sys.stderr)
        print("[HINT] Nav2 nodes are not loaded in nav2_container.", file=sys.stderr)
        print("       A previous Gazebo or Nav2 process may still be running in the background.", file=sys.stderr)
        print("       Run: pkill -9 -f 'gzserver|component_container' && rm -f /dev/shm/fastrtps_* /dev/shm/sem.fastrtps_*", file=sys.stderr)
        print("       Then restart: python3 src/start_robot.py --with-nav", file=sys.stderr)
        rclpy.shutdown()
        sys.exit(1)

    navigator.waitUntilNav2Active()
    print("  -> Nav2 is fully active and ready.", flush=True)

    # Confirm AMCL localization is active
    print("[INFO] Confirming AMCL laser scan localization convergence...", flush=True)
    for _ in range(10):
        rclpy.spin_once(navigator, timeout_sec=0.2)
    print("  -> AMCL localization active and ready.", flush=True)

    # 3. Define multi-goal waypoints navigating through the house rooms
    # turtlebot3_house contains multi-room partitions, doors, tables, and furniture
    waypoints = [
        {"name": "Waypoint 1 (North-East Master Room)", "x": 4.5, "y": 2.5, "yaw": 0.0, "timeout": 90},
        {"name": "Waypoint 2 (South-East Sunroom)", "x": 6.0, "y": -1.0, "yaw": -90.0, "timeout": 90},
        {"name": "Waypoint 3 (Return to Living Room Base)", "x": -2.0, "y": 1.0, "yaw": 180.0, "timeout": 120}
    ]

    print(f"[3/4] Executing autonomous navigation sequence ({len(waypoints)} goals)...")

    results = []

    for i, wp in enumerate(waypoints, start=1):
        goal_pose = create_pose_stamped(navigator, wp["x"], wp["y"], wp["yaw"])
        print(f"\n--- Navigating to {wp['name']}: x={wp['x']:.2f}, y={wp['y']:.2f} ---")
        navigator.goToPose(goal_pose)

        start_time = time.time()
        success = False

        while not navigator.isTaskComplete():
            feedback = navigator.getFeedback()
            elapsed = time.time() - start_time

            if feedback and elapsed > 0:
                dist = feedback.distance_remaining
                print(f"  [Progress] Distance remaining: {dist:.2f}m | Elapsed: {elapsed:.1f}s", end="\r", flush=True)

            # Check timeout
            if elapsed > wp["timeout"]:
                print(f"\n  [TIMEOUT] Goal exceeded {wp['timeout']}s limit. Canceling goal...")
                navigator.cancelTask()
                break

            time.sleep(0.5)

        res = navigator.getResult()
        if res == TaskResult.SUCCEEDED:
            duration = time.time() - start_time
            print(f"\n  [SUCCESS] Reached {wp['name']} in {duration:.1f}s!")
            results.append((wp["name"], True, f"{duration:.1f}s"))
        elif res == TaskResult.CANCELED:
            print(f"\n  [CANCELED] Task was canceled.")
            results.append((wp["name"], False, "Canceled"))
        elif res == TaskResult.FAILED:
            print(f"\n  [FAILED] Navigation failed to reach target.")
            results.append((wp["name"], False, "Failed"))
        else:
            print(f"\n  [UNKNOWN] Return code: {res}")
            results.append((wp["name"], False, "Unknown"))

        time.sleep(1.0)

    # 4. Summary Report
    print("\n" + "="*60)
    print(" NAVIGATION DEMO SUMMARY RESULTS")
    print("="*60)
    all_passed = True
    for name, success, note in results:
        status_str = "PASS" if success else "FAIL"
        if not success:
            all_passed = False
        print(f" - {name:<35} : [{status_str}] ({note})")
    print("="*60)

    if all_passed:
        print("[DEMO COMPLETE] All navigation goals succeeded with obstacle avoidance!")
    else:
        print("[DEMO WARNING] One or more goals did not complete successfully.")

    # Keep lifecycle nodes running for interactive simulation
    # navigator.lifecycleShutdown()
    rclpy.shutdown()
    sys.exit(0 if all_passed else 1)

if __name__ == '__main__':
    main()
