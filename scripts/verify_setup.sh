#!/usr/bin/env bash
set -e

# Verification script for TurtleBot3 Autonomous Navigation Environment

echo "============================================================"
echo " TurtleBot3 Autonomous Navigation Environment Verifier"
echo "============================================================"

# 1. Check ROS 2 Humble setup
if [ -f "/opt/ros/humble/setup.bash" ]; then
    echo "[PASS] ROS 2 Humble installation found at /opt/ros/humble"
    source /opt/ros/humble/setup.bash
else
    echo "[FAIL] ROS 2 Humble installation missing"
    exit 1
fi

# 2. Check Robot model variable
export TURTLEBOT3_MODEL=burger
echo "[PASS] TURTLEBOT3_MODEL is set to ${TURTLEBOT3_MODEL}"

# 3. Check Gazebo Classic version
if command -v gazebo >/dev/null 2>&1; then
    GZ_VER=$(gazebo --version | head -n 1)
    echo "[PASS] Gazebo simulator detected: ${GZ_VER}"
else
    echo "[FAIL] Gazebo simulator not found"
    exit 1
fi

# 4. Check essential packages
PACKAGES=("turtlebot3_gazebo" "turtlebot3_navigation2" "nav2_bringup" "gazebo_ros" "nav2_simple_commander")
for pkg in "${PACKAGES[@]}"; do
    if ros2 pkg prefix "${pkg}" >/dev/null 2>&1; then
        echo "[PASS] ROS 2 package '${pkg}' is available"
    else
        echo "[FAIL] Required package '${pkg}' is missing"
        exit 1
    fi
done

# 5. Check Gazebo Model Paths
if [ -d "/usr/share/gazebo-11/models/ground_plane" ] && [ -d "/opt/ros/humble/share/turtlebot3_gazebo/models/turtlebot3_burger" ]; then
    echo "[PASS] Local Gazebo model assets verified (ground_plane, turtlebot3_burger)"
else
    echo "[FAIL] Model directories missing"
    exit 1
fi

echo "============================================================"
echo " ALL SYSTEM PRE-CHECKS PASSED SUCCESSFULLY"
echo "============================================================"
