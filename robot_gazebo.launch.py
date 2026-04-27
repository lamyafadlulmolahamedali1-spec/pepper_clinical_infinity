#!/usr/bin/env python3
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess
import os

def generate_launch_description():
    urdf_file = os.path.expanduser('~/ros2_ws/src/simple_robot/urdf/simple_robot.urdf')
    
    return LaunchDescription([
        ExecuteProcess(
            cmd=['gazebo', '--verbose', 'worlds/empty.world'],
            output='screen'
        ),
        
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            arguments=[urdf_file]
        ),
        
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='joint_state_publisher_gui',
            output='screen'
        ),
        
        Node(
            package='gazebo_ros',
            executable='spawn_entity.py',
            name='spawn_robot',
            arguments=['-entity', 'robot', '-file', urdf_file, '-x', '0', '-y', '0', '-z', '0.1'],
            output='screen'
        ),
    ])
