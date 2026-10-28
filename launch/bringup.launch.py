#!/usr/bin/env python3
"""
Full system bringup: Launches Gazebo simulation, robot spawn, Nav2 stack, and RViz2.
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sim_launch = os.path.join(pkg_dir, 'launch', 'simulation.launch.py')
    nav_launch = os.path.join(pkg_dir, 'launch', 'navigation.launch.py')
    default_map = os.path.join(pkg_dir, 'maps', 'map.yaml')
    default_params = os.path.join(pkg_dir, 'config', 'nav2_params.yaml')

    gui = LaunchConfiguration('gui', default='true')
    use_rviz = LaunchConfiguration('use_rviz', default='true')

    declare_gui = DeclareLaunchArgument(
        'gui', default_value='true',
        description='Launch Gazebo GUI client')
    declare_use_rviz = DeclareLaunchArgument(
        'use_rviz', default_value='true',
        description='Launch RViz2')

    sim_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(sim_launch),
        launch_arguments={'gui': gui, 'use_sim_time': 'true'}.items()
    )

    nav_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(nav_launch),
        launch_arguments={
            'use_rviz': use_rviz,
            'use_sim_time': 'true',
            'map': default_map,
            'params_file': default_params
        }.items()
    )

    ld = LaunchDescription()
    ld.add_action(declare_gui)
    ld.add_action(declare_use_rviz)
    ld.add_action(sim_cmd)
    ld.add_action(nav_cmd)

    return ld
