"""
asd_system.launch.py
Brings up ALL ROS 2 nodes for the ASD Companion Robot.

Nodes launched:
  - perception_node      : YOLOv8 object detection + affect recognition
  - sensor_fusion_node   : fuses vision/audio into child state estimate
  - tie_node             : Therapeutic Interaction Engine (behavior tree)
  - robot_controller     : translates TIE commands → Gazebo robot actions
  - dashboard_bridge     : publishes session logs to Flask dashboard
"""

import os
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, IncludeLaunchDescription,
    GroupAction, TimerAction
)
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node, PushRosNamespace
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():

    # ── Arguments ────────────────────────────────────────────
    use_rviz_arg = DeclareLaunchArgument(
        "use_rviz", default_value="false",
        description="Launch RViz2 visualizer"
    )
    child_profile_arg = DeclareLaunchArgument(
        "child_profile", default_value="default",
        description="Child therapy profile to load from dashboard DB"
    )
    log_level_arg = DeclareLaunchArgument(
        "log_level", default_value="info",
        description="ROS log level: debug | info | warn | error"
    )

    use_rviz       = LaunchConfiguration("use_rviz")
    child_profile  = LaunchConfiguration("child_profile")
    log_level      = LaunchConfiguration("log_level")

    pkg_bringup    = FindPackageShare("asd_bringup")
    pkg_perception = FindPackageShare("asd_perception")
    pkg_tie        = FindPackageShare("asd_tie")
    pkg_controller = FindPackageShare("asd_robot_controller")

    # ── 1. Perception Node ───────────────────────────────────
    perception_node = Node(
        package="asd_perception",
        executable="perception_node",
        name="perception_node",
        output="screen",
        parameters=[
            PathJoinSubstitution([pkg_perception, "config", "perception_params.yaml"]),
            {"yolo_model": "yolov8n.pt"},
            {"affect_backends": ["deepface", "fer"]},
            {"camera_topic": "/pepper/camera/image_raw"},
            {"audio_topic":  "/pepper/microphone/audio_raw"},
        ],
        arguments=["--ros-args", "--log-level", log_level],
    )

    # ── 2. Sensor Fusion / State Estimator ───────────────────
    sensor_fusion_node = Node(
        package="asd_perception",
        executable="sensor_fusion_node",
        name="sensor_fusion_node",
        output="screen",
        parameters=[{
            "fusion_rate_hz": 10,
            "emotion_smoothing_window": 5,
            "activity_confidence_threshold": 0.6,
        }],
        arguments=["--ros-args", "--log-level", log_level],
    )

    # ── 3. Therapeutic Interaction Engine (TIE) ──────────────
    tie_node = Node(
        package="asd_tie",
        executable="tie_node",
        name="tie_node",
        output="screen",
        parameters=[
            PathJoinSubstitution([pkg_tie, "config", "tie_params.yaml"]),
            {"child_profile":   child_profile},
            {"bt_xml_file":     PathJoinSubstitution(
                [pkg_tie, "behavior_trees", "main_therapy_bt.xml"])},
            {"therapy_protocol": "ABA_TEACCH_HYBRID"},
        ],
        arguments=["--ros-args", "--log-level", log_level],
    )

    # ── 4. Robot Controller ──────────────────────────────────
    controller_node = Node(
        package="asd_robot_controller",
        executable="robot_controller_node",
        name="robot_controller_node",
        output="screen",
        parameters=[
            PathJoinSubstitution([pkg_controller, "config", "controller_params.yaml"]),
            {"robot_name": "pepper"},
            {"sim_mode":   True},
        ],
        arguments=["--ros-args", "--log-level", log_level],
    )

    # ── 5. Dashboard Bridge ──────────────────────────────────
    dashboard_bridge_node = Node(
        package="asd_bringup",
        executable="dashboard_bridge_node",
        name="dashboard_bridge_node",
        output="screen",
        parameters=[{
            "dashboard_url":      "http://localhost:5000",
            "publish_rate_hz":    1,
            "session_log_topic":  "/asd/session_log",
        }],
        arguments=["--ros-args", "--log-level", log_level],
    )

    # ── 6. RViz2 (optional) ──────────────────────────────────
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        condition=IfCondition(use_rviz),
        arguments=[
            "-d", PathJoinSubstitution([pkg_bringup, "rviz", "asd_robot.rviz"])
        ],
    )

    return LaunchDescription([
        use_rviz_arg,
        child_profile_arg,
        log_level_arg,
        perception_node,
        TimerAction(period=2.0, actions=[sensor_fusion_node]),
        TimerAction(period=4.0, actions=[tie_node]),
        TimerAction(period=5.0, actions=[controller_node]),
        TimerAction(period=6.0, actions=[dashboard_bridge_node]),
        rviz_node,
    ])
