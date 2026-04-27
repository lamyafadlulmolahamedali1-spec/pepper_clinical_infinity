#!/usr/bin/env python3
"""
Pepper + ASD System - Clean Launch
تشغيل Pepper (Docker) مع نظام ASD (ROS2) بدون تعارض
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess, TimerAction, SetEnvironmentVariable
import os

def generate_launch_description():
    # التأكد من أن ROS2 فقط هو النشط
    set_ros2_env = SetEnvironmentVariable(
        name='ROS_DISTRO',
        value='humble'
    )
    
    # تشغيل مشروع Pepper (Docker)
    pepper_docker = ExecuteProcess(
        cmd=['bash', os.path.expanduser('~/Desktop/pepper_project/start_pepper.sh')],
        output='screen',
        shell=True
    )
    
    # عقد ASD
    child_node = Node(
        package='asd_therapy_framework',
        executable='child_behavior_model',
        name='child_behavior_model',
        output='screen'
    )
    
    affect_node = Node(
        package='asd_therapy_framework',
        executable='affect_recognizer',
        name='affect_recognizer',
        output='screen'
    )
    
    state_node = Node(
        package='asd_therapy_framework',
        executable='state_estimator',
        name='state_estimator',
        output='screen'
    )
    
    tie_node = Node(
        package='asd_therapy_framework',
        executable='therapy_engine',
        name='therapy_engine',
        output='screen'
    )
    
    dashboard_node = Node(
        package='asd_therapy_framework',
        executable='dashboard_node',
        name='dashboard_node',
        output='screen'
    )
    
    return LaunchDescription([
        set_ros2_env,
        pepper_docker,
        TimerAction(period=8.0, actions=[child_node]),
        TimerAction(period=9.0, actions=[affect_node]),
        TimerAction(period=10.0, actions=[state_node]),
        TimerAction(period=11.0, actions=[tie_node]),
        TimerAction(period=12.0, actions=[dashboard_node]),
    ])
