"""
pepper_world.launch.py
Launches the Pepper robot inside a Gazebo Fortress therapy room world.

Requires:
  - pepper_ign_moveit2  (HibaSekkat/pepper_ign_moveit2)
  - pepper_description  (ros-naoqi/pepper_robot)
  - ros_gz_sim          (gazebosim/ros_gz)
  - gz_ros2_control
"""

import os
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, IncludeLaunchDescription,
    SetEnvironmentVariable, RegisterEventHandler
)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    LaunchConfiguration, Command, PathJoinSubstitution, FindExecutable
)
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():

    # ── Arguments ────────────────────────────────────────────
    world_arg = DeclareLaunchArgument(
        "world", default_value="therapy_room.sdf",
        description="Gazebo world SDF file"
    )
    use_gui_arg = DeclareLaunchArgument(
        "gz_gui", default_value="true",
        description="Launch Gazebo with GUI"
    )
    robot_x_arg = DeclareLaunchArgument("x", default_value="0.0")
    robot_y_arg = DeclareLaunchArgument("y", default_value="0.0")
    robot_z_arg = DeclareLaunchArgument("z", default_value="0.0")

    world    = LaunchConfiguration("world")
    gz_gui   = LaunchConfiguration("gz_gui")
    robot_x  = LaunchConfiguration("x")
    robot_y  = LaunchConfiguration("y")
    robot_z  = LaunchConfiguration("z")

    pkg_sim  = FindPackageShare("asd_pepper_sim")
    pkg_desc = FindPackageShare("asd_pepper_description")

    # ── Pepper URDF via xacro ─────────────────────────────────
    robot_description = Command([
        FindExecutable(name="xacro"), " ",
        PathJoinSubstitution([pkg_desc, "urdf", "pepper_gz.urdf.xacro"]),
        " use_sim:=true",
    ])

    # ── Robot State Publisher ─────────────────────────────────
    robot_state_pub = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[{
            "robot_description": robot_description,
            "use_sim_time": True,
        }],
    )

    # ── Gazebo Fortress ───────────────────────────────────────
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare("ros_gz_sim"),
                "launch", "gz_sim.launch.py"
            ])
        ]),
        launch_arguments={
            "gz_args": [
                "-r ",                                          # run immediately
                PathJoinSubstitution([pkg_sim, "worlds", world]),
                " --headless-rendering" if False else "",       # set True for CI
            ],
        }.items(),
    )

    # ── Spawn Pepper in Gazebo ────────────────────────────────
    spawn_pepper = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=[
            "-name",  "pepper",
            "-topic", "robot_description",
            "-x", robot_x, "-y", robot_y, "-z", robot_z,
        ],
        output="screen",
    )

    # ── ROS–Gazebo Bridge ─────────────────────────────────────
    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="ros_gz_bridge",
        output="screen",
        arguments=[
            # clock
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
            # Camera
            "/pepper/camera/image_raw@sensor_msgs/msg/Image[gz.msgs.Image",
            "/pepper/camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo",
            # Depth
            "/pepper/depth/image_raw@sensor_msgs/msg/Image[gz.msgs.Image",
            "/pepper/depth/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked",
            # Audio (mono microphone)
            "/pepper/microphone/audio_raw@audio_common_msgs/msg/AudioData[gz.msgs.AudioData",
            # Joint states
            "/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model",
            # IMU
            "/pepper/imu@sensor_msgs/msg/Imu[gz.msgs.IMU",
            # Cmd vel
            "/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist",
        ],
    )

    # ── gz_ros2_control spawner ───────────────────────────────
    joint_state_broadcaster = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
        output="screen",
    )
    pepper_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["pepper_joint_trajectory_controller", "--controller-manager", "/controller_manager"],
        output="screen",
    )

    # Spawn controllers AFTER robot is ready
    spawn_controllers = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=spawn_pepper,
            on_exit=[joint_state_broadcaster, pepper_controller],
        )
    )

    return LaunchDescription([
        world_arg, use_gui_arg,
        robot_x_arg, robot_y_arg, robot_z_arg,
        robot_state_pub,
        gazebo,
        spawn_pepper,
        bridge,
        spawn_controllers,
    ])
