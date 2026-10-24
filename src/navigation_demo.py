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
    rclpy.init()
    navigator = BasicNavigator()

    print("\n" + "="*60)
    print(" TURTLEBOT3 AUTONOMOUS NAVIGATION DEMONSTRATOR")
    print("="*60)

    # 1. Set Initial Pose (matches spawn pose in turtlebot3_world)
    init_x, init_y, init_yaw = -2.0, -0.5, 0.0
    print(f"[1/4] Setting initial pose: x={init_x}, y={init_y}, yaw={init_yaw}°")
    initial_pose = create_pose_stamped(navigator, init_x, init_y, init_yaw)
    navigator.setInitialPose(initial_pose)

    # 2. Wait for Nav2 active
    print("[2/4] Waiting for Nav2 stack lifecycle nodes to activate...")
    navigator.waitUntilNav2Active()
    print("  -> Nav2 is fully active and ready.")

    # 3. Define multi-goal waypoints navigating through the obstacle course
    # turtlebot3_world contains columns and barrier walls
    waypoints = [
        {"name": "Waypoint 1 (Center Hallway)", "x": 0.0, "y": 0.0, "yaw": 0.0, "timeout": 60},
        {"name": "Waypoint 2 (East Obstacle Perimeter)", "x": 1.2, "y": -0.8, "yaw": 90.0, "timeout": 60},
        {"name": "Waypoint 3 (Return to Base)", "x": -2.0, "y": -0.5, "yaw": 180.0, "timeout": 90}
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
                print(f"  [Progress] Distance remaining: {dist:.2f}m | Elapsed: {elapsed:.1f}s", end="\r")

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

    navigator.lifecycleShutdown()
    rclpy.shutdown()
    sys.exit(0 if all_passed else 1)

if __name__ == '__main__':
    main()
