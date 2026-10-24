#!/usr/bin/env python3
"""
Simulation launch file for TurtleBot3 Burger in Gazebo Classic.
Ensures correct GAZEBO_MODEL_PATH and GAZEBO_MODEL_DATABASE_URI to prevent network hangs.
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_world = os.path.join(pkg_dir, 'worlds', 'turtlebot3_world.world')

    pkg_tb3_gazebo = get_package_share_directory('turtlebot3_gazebo')
    pkg_gazebo_ros = get_package_share_directory('gazebo_ros')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    gui = LaunchConfiguration('gui', default='true')
    world = LaunchConfiguration('world', default=default_world)
    x_pose = LaunchConfiguration('x_pose', default='-2.0')
    y_pose = LaunchConfiguration('y_pose', default='-0.5')
    z_pose = LaunchConfiguration('z_pose', default='0.01')

    # Configure robust model paths and disable remote model database lookup
    model_paths = [
        '/usr/share/gazebo-11/models',
        os.path.join(pkg_tb3_gazebo, 'models'),
        os.path.join(pkg_dir, 'models')
    ]
    existing_model_path = os.environ.get('GAZEBO_MODEL_PATH', '')
    if existing_model_path:
        model_paths.append(existing_model_path)
    combined_model_path = ':'.join([p for p in model_paths if os.path.exists(p)])

    set_model_path = SetEnvironmentVariable('GAZEBO_MODEL_PATH', combined_model_path)
    set_db_uri = SetEnvironmentVariable('GAZEBO_MODEL_DATABASE_URI', '')
    set_tb3_model = SetEnvironmentVariable('TURTLEBOT3_MODEL', 'burger')

    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time', default_value='true',
        description='Use simulation (Gazebo) clock if true')
    declare_gui = DeclareLaunchArgument(
        'gui', default_value='true',
        description='Set to "false" to run headless')
    declare_world = DeclareLaunchArgument(
        'world', default_value=default_world,
        description='Full path to world model file to load')
    declare_x_pose = DeclareLaunchArgument(
        'x_pose', default_value='-2.0', description='Initial robot X coordinate')
    declare_y_pose = DeclareLaunchArgument(
        'y_pose', default_value='-0.5', description='Initial robot Y coordinate')
    declare_z_pose = DeclareLaunchArgument(
        'z_pose', default_value='0.01', description='Initial robot Z coordinate')

    # gzserver
    gzserver_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, 'launch', 'gzserver.launch.py')
        ),
        launch_arguments={'world': world}.items()
    )

    # gzclient
    gzclient_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, 'launch', 'gzclient.launch.py')
        ),
        condition=IfCondition(gui)
    )

    # robot_state_publisher
    urdf_path = os.path.join(
        get_package_share_directory('turtlebot3_description'),
        'urdf',
        'turtlebot3_burger.urdf'
    )
    with open(urdf_path, 'r') as f:
        robot_desc = f.read()

    robot_state_publisher_cmd = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'robot_description': robot_desc
        }]
    )

    # spawn robot entity
    model_sdf = os.path.join(pkg_tb3_gazebo, 'models', 'turtlebot3_burger', 'model.sdf')
    spawn_turtlebot_cmd = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-entity', 'burger',
            '-file', model_sdf,
            '-x', x_pose,
            '-y', y_pose,
            '-z', z_pose,
            '-timeout', '60'
        ],
        output='screen'
    )

    ld = LaunchDescription()
    ld.add_action(set_model_path)
    ld.add_action(set_db_uri)
    ld.add_action(set_tb3_model)
    ld.add_action(declare_use_sim_time)
    ld.add_action(declare_gui)
    ld.add_action(declare_world)
    ld.add_action(declare_x_pose)
    ld.add_action(declare_y_pose)
    ld.add_action(declare_z_pose)
    ld.add_action(gzserver_cmd)
    ld.add_action(gzclient_cmd)
    ld.add_action(robot_state_publisher_cmd)
    ld.add_action(spawn_turtlebot_cmd)

    return ld
