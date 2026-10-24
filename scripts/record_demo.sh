#!/usr/bin/env bash
set -e

PROJECT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ROS_SETUP="/opt/ros/humble/setup.bash"
OUTPUT_MP4="${PROJECT_DIR}/media/autonomous_navigation_demo.mp4"
OUTPUT_GIF="${PROJECT_DIR}/media/demo.gif"

echo "============================================================"
echo " TurtleBot3 Autonomous Navigation Recording Session"
echo "============================================================"

# Ensure environment
source "${ROS_SETUP}"
export TURTLEBOT3_MODEL=burger
export GAZEBO_MODEL_PATH="/usr/share/gazebo-11/models:/opt/ros/humble/share/turtlebot3_gazebo/models:${GAZEBO_MODEL_PATH}"
export GAZEBO_MODEL_DATABASE_URI=""

# Cleanup existing processes
killall -9 gzserver gzclient rviz2 python3 >/dev/null 2>&1 || true
sleep 1

# Launch full system bringup (Gazebo simulation + Nav2 stack)
echo "[1/5] Launching Simulation and Nav2 Bringup..."
ros2 launch "${PROJECT_DIR}/launch/bringup.launch.py" gui:=false use_rviz:=false > /tmp/bringup.log 2>&1 &
BRINGUP_PID=$!

cleanup() {
    echo "[*] Cleaning up processes..."
    kill -9 "${REC_PID}" >/dev/null 2>&1 || true
    kill -9 "${BRINGUP_PID}" >/dev/null 2>&1 || true
    killall -9 gzserver gzclient rviz2 >/dev/null 2>&1 || true
}
trap cleanup EXIT

# Wait for system readiness
echo "[2/5] Waiting for Gazebo and Nav2 lifecycle nodes..."
for i in {1..60}; do
    if ros2 lifecycle get /planner_server 2>/dev/null | grep -q "active"; then
        echo "  -> Nav2 is active and ready!"
        break
    fi
    sleep 1
done

sleep 3

# Start Multi-Panel Video Recorder
echo "[3/5] Starting Multi-Panel Video Recorder (${OUTPUT_MP4})..."
mkdir -p "${PROJECT_DIR}/media"
python3 "${PROJECT_DIR}/scripts/record_demo_visualizer.py" "${OUTPUT_MP4}" 90 > /tmp/recorder.log 2>&1 &
REC_PID=$!

sleep 3

# Run Autonomous Navigation Demo
echo "[4/5] Executing Autonomous Navigation Demo..."
python3 "${PROJECT_DIR}/src/navigation_demo.py"

sleep 3

# Stop Recording
echo "[5/5] Finalizing Recording and generating GIF..."
kill -INT "${REC_PID}" >/dev/null 2>&1 || true
wait "${REC_PID}" 2>/dev/null || true

# Generate animated GIF for README preview
echo "  -> Generating demo.gif..."
ffmpeg -y -ss 00:00:05 -i "${OUTPUT_MP4}" -t 30 \
       -vf "fps=10,scale=800:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" \
       "${OUTPUT_GIF}" > /dev/null 2>&1 || true

echo "============================================================"
echo " DEMO RECORDING FINISHED SUCCESSFULLY"
echo " MP4: ${OUTPUT_MP4}"
echo " GIF: ${OUTPUT_GIF}"
echo "============================================================"
