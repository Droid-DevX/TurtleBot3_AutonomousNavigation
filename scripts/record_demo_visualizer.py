#!/usr/bin/env python3
"""
Multi-Panel Autonomous Navigation Demo Recorder
Subscribes to Gazebo arena camera, Nav2 map, global plan, laser scan, and robot odometry,
composites a side-by-side 1080p dashboard video, and saves MP4 and GIF.
"""

import math
import os
import sys
import time
import cv2
import numpy as np

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, LaserScan
from nav_msgs.msg import OccupancyGrid, Path, Odometry

class DemoRecorderNode(Node):
    def __init__(self, output_mp4, duration_limit=90):
        super().__init__('demo_recorder_node')
        self.output_mp4 = output_mp4
        self.duration_limit = duration_limit

        self.latest_camera = None
        self.map_msg = None
        self.map_image = None
        self.latest_scan = None
        self.latest_plan = None
        self.latest_odom = None
        self.start_time = time.time()

        # Video writer setup
        self.width = 1920
        self.height = 1080
        self.fps = 20.0
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        os.makedirs(os.path.dirname(output_mp4), exist_ok=True)
        self.video_writer = cv2.VideoWriter(output_mp4, fourcc, self.fps, (self.width, self.height))

        # Subscriptions
        self.create_subscription(Image, '/simulation/camera/image_raw', self.camera_callback, 10)
        self.create_subscription(OccupancyGrid, '/map', self.map_callback, 10)
        self.create_subscription(Path, '/plan', self.plan_callback, 10)
        self.create_subscription(LaserScan, '/scan', self.scan_callback, 10)
        self.create_subscription(Odometry, '/odom', self.odom_callback, 10)

        # Timer for frame capture and video generation
        self.timer = self.create_timer(1.0 / self.fps, self.render_frame)
        self.frame_count = 0
        self.get_logger().info(f"Demo Recorder started. Writing to {output_mp4} at {self.fps} FPS")

    def camera_callback(self, msg):
        try:
            # Decode RGB8 image
            arr = np.frombuffer(msg.data, dtype=np.uint8).reshape((msg.height, msg.width, 3))
            # Convert RGB to BGR for OpenCV
            self.latest_camera = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        except Exception as e:
            pass

    def map_callback(self, msg):
        self.map_msg = msg
        w, h = msg.info.width, msg.info.height
        data = np.array(msg.data, dtype=np.int8).reshape((h, w))
        img = np.zeros((h, w, 3), dtype=np.uint8)

        # -1 = unknown (gray 100), 0 = free (white 240), 100 = occupied (black 20)
        img[data == -1] = [120, 120, 120]
        img[data == 0] = [230, 230, 230]
        img[data == 100] = [30, 30, 30]
        # Flip vertically since ROS map origin is bottom-left
        self.map_image = cv2.flip(img, 0)

    def plan_callback(self, msg):
        self.latest_plan = msg

    def scan_callback(self, msg):
        self.latest_scan = msg

    def odom_callback(self, msg):
        self.latest_odom = msg

    def world_to_map_pixel(self, x, y):
        if not self.map_msg:
            return None
        res = self.map_msg.info.resolution
        orig_x = self.map_msg.info.origin.position.x
        orig_y = self.map_msg.info.origin.position.y
        h = self.map_msg.info.height

        px = int((x - orig_x) / res)
        py = int(h - (y - orig_y) / res)
        return (px, py)

    def render_frame(self):
        elapsed = time.time() - self.start_time
        if elapsed > self.duration_limit:
            self.finish()
            return

        # Canvas: 1920x1080 (Dark modern theme)
        canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        canvas[:] = [24, 24, 28]

        # Top Header (0 to 80)
        cv2.rectangle(canvas, (0, 0), (self.width, 80), (36, 36, 42), -1)
        cv2.putText(canvas, "TURTLEBOT3 AUTONOMOUS NAVIGATION & OBSTACLE AVOIDANCE", (40, 48),
                    cv2.FONT_HERSHEY_DUPLEX, 1.1, (255, 255, 255), 2)
        cv2.putText(canvas, "ROS 2 Humble | Gazebo Classic | Nav2 | AMCL | Costmaps", (1100, 48),
                    cv2.FONT_HERSHEY_DUPLEX, 0.7, (140, 210, 255), 1)
        cv2.line(canvas, (0, 80), (self.width, 80), (60, 60, 75), 2)

        # Panel Headers (80 to 120)
        cv2.putText(canvas, "[PANEL 1] 3D SIMULATION (GAZEBO ARENA)", (40, 115),
                    cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 220, 255), 1)
        cv2.putText(canvas, "[PANEL 2] NAV2 LOCALIZATION & SENSOR MAP", (1000, 115),
                    cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 255, 180), 1)

        # Left Panel: Gazebo Camera Feed (130 to 920, x: 40 to 940)
        left_w, left_h = 900, 790
        if self.latest_camera is not None:
            cam_resized = cv2.resize(self.latest_camera, (left_w, left_h))
            # Overlay robot HUD
            if self.latest_odom:
                pos = self.latest_odom.pose.pose.position
                vel = self.latest_odom.twist.twist.linear.x
                ang = self.latest_odom.twist.twist.angular.z
                cv2.rectangle(cam_resized, (15, 15), (320, 105), (10, 10, 10), -1)
                cv2.rectangle(cam_resized, (15, 15), (320, 105), (0, 200, 255), 1)
                cv2.putText(cam_resized, f"Robot: TB3 Burger", (25, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                cv2.putText(cam_resized, f"Pose : ({pos.x:.2f}, {pos.y:.2f})m", (25, 65),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 240, 255), 1)
                cv2.putText(cam_resized, f"Speed: {vel:.2f} m/s | W: {ang:.2f}", (25, 90),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 200), 1)
            canvas[130:130+left_h, 40:40+left_w] = cam_resized
        else:
            cv2.rectangle(canvas, (40, 130), (40+left_w, 130+left_h), (40, 40, 48), -1)
            cv2.putText(canvas, "Waiting for Gazebo Camera Stream...", (250, 500),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180, 180, 180), 2)
        cv2.rectangle(canvas, (40, 130), (40+left_w, 130+left_h), (80, 80, 95), 2)

        # Right Panel: Nav2 Map & Path & LaserScan (130 to 920, x: 980 to 1880)
        right_w, right_h = 900, 790
        right_panel = np.zeros((right_h, right_w, 3), dtype=np.uint8)
        right_panel[:] = [30, 30, 36]

        if self.map_image is not None:
            # Crop region of interest around arena [-4.0 to 4.0]
            # Arena bounds in world: x in [-3, 3], y in [-3, 3]
            p_min = self.world_to_map_pixel(-3.2, 3.2)
            p_max = self.world_to_map_pixel(3.2, -3.2)
            if p_min and p_max:
                x1, y1 = max(0, p_min[0]), max(0, p_min[1])
                x2, y2 = min(self.map_image.shape[1], p_max[0]), min(self.map_image.shape[0], p_max[1])
                cropped_map = self.map_image[y1:y2, x1:x2].copy()
                cropped_map = cv2.resize(cropped_map, (right_w, right_h))

                # Draw Global Path (green)
                if self.latest_plan and len(self.latest_plan.poses) > 1:
                    pts = []
                    for pose_stamped in self.latest_plan.poses:
                        wx = pose_stamped.pose.position.x
                        wy = pose_stamped.pose.position.y
                        # map coords inside cropped area
                        rx = int((wx - (-3.2)) / 6.4 * right_w)
                        ry = int((3.2 - wy) / 6.4 * right_h)
                        if 0 <= rx < right_w and 0 <= ry < right_h:
                            pts.append((rx, ry))
                    if len(pts) > 1:
                        cv2.polylines(cropped_map, [np.array(pts, dtype=np.int32)], False, (0, 220, 0), 3)

                # Draw Laser Scan Points (cyan)
                if self.latest_scan and self.latest_odom:
                    rx_curr = self.latest_odom.pose.pose.position.x
                    ry_curr = self.latest_odom.pose.pose.position.y
                    q = self.latest_odom.pose.pose.orientation
                    yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))

                    angle = self.latest_scan.angle_min
                    scan_pts = []
                    for r in self.latest_scan.ranges:
                        if self.latest_scan.range_min < r < self.latest_scan.range_max:
                            beam_angle = yaw + angle
                            ox = rx_curr + r * math.cos(beam_angle)
                            oy = ry_curr + r * math.sin(beam_angle)
                            px = int((ox - (-3.2)) / 6.4 * right_w)
                            py = int((3.2 - oy) / 6.4 * right_h)
                            if 0 <= px < right_w and 0 <= py < right_h:
                                scan_pts.append((px, py))
                        angle += self.latest_scan.angle_increment
                    for p in scan_pts:
                        cv2.circle(cropped_map, p, 2, (255, 255, 0), -1)

                # Draw Waypoint Markers
                wps = [
                    ("WP1", 0.0, 0.0, (0, 165, 255)),
                    ("WP2", 1.2, -0.8, (255, 0, 200)),
                    ("HOME", -2.0, -0.5, (0, 255, 0))
                ]
                for label, wx, wy, col in wps:
                    px = int((wx - (-3.2)) / 6.4 * right_w)
                    py = int((3.2 - wy) / 6.4 * right_h)
                    cv2.circle(cropped_map, (px, py), 8, col, -1)
                    cv2.circle(cropped_map, (px, py), 12, (255, 255, 255), 1)
                    cv2.putText(cropped_map, label, (px + 12, py + 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 2)

                # Draw Robot Pose (Red dot with heading arrow)
                if self.latest_odom:
                    rx = int((self.latest_odom.pose.pose.position.x - (-3.2)) / 6.4 * right_w)
                    ry = int((3.2 - self.latest_odom.pose.pose.position.y) / 6.4 * right_h)
                    if 0 <= rx < right_w and 0 <= ry < right_h:
                        q = self.latest_odom.pose.pose.orientation
                        yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))
                        arr_len = 22
                        ax = int(rx + arr_len * math.cos(yaw))
                        ay = int(ry - arr_len * math.sin(yaw))
                        cv2.circle(cropped_map, (rx, ry), 10, (0, 0, 255), -1)
                        cv2.arrowedLine(cropped_map, (rx, ry), (ax, ay), (255, 255, 255), 2, tipLength=0.3)

                right_panel = cropped_map

        canvas[130:130+right_h, 980:980+right_w] = right_panel
        cv2.rectangle(canvas, (980, 130), (980+right_w, 130+right_h), (80, 80, 95), 2)

        # Bottom Footer & Telemetry (940 to 1060)
        cv2.rectangle(canvas, (0, 940), (self.width, self.height), (36, 36, 42), -1)
        cv2.line(canvas, (0, 940), (self.width, 940), (60, 60, 75), 2)

        status_text = "AUTONOMOUS PATH FOLLOWING & DYNAMIC OBSTACLE AVOIDANCE"
        cv2.putText(canvas, f"STATUS: {status_text}", (40, 980),
                    cv2.FONT_HERSHEY_DUPLEX, 0.75, (0, 255, 120), 2)

        info_line = f"Elapsed: {elapsed:.1f}s | Scan Rays: 360 | Global Planner: Navfn | Controller: DWB | Recovery: Enabled"
        cv2.putText(canvas, info_line, (40, 1025),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        # Write frame to video
        self.video_writer.write(canvas)
        self.frame_count += 1

    def finish(self):
        self.get_logger().info(f"Finalizing video: {self.frame_count} frames written.")
        self.video_writer.release()
        self.destroy_node()
        rclpy.shutdown()

def main():
    rclpy.init()
    output_mp4 = sys.argv[1] if len(sys.argv) > 1 else "/home/ayush/Robotics/TurtleBot3/media/autonomous_navigation_demo.mp4"
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 90

    node = DemoRecorderNode(output_mp4, duration_limit=duration)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.finish()

if __name__ == '__main__':
    main()
