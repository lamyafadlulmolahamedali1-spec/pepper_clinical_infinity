#!/usr/bin/env python3
"""
robot_controller_node.py
─────────────────────────
Translates high-level TIE JSON commands into low-level
ROS 2 / Gazebo actions for the simulated Pepper robot.

Subscribes:
  /asd/robot_command          (std_msgs/String JSON)

Publishes:
  /cmd_vel                    (geometry_msgs/Twist)     – base motion
  /pepper/speech              (std_msgs/String)         – TTS text
  /pepper/gesture             (std_msgs/String)         – gesture name
  /pepper/led                 (std_msgs/String)         – LED pattern
  /pepper/joint_cmd           (sensor_msgs/JointState)  – direct joints
"""

import json
import math
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration


# ── Gesture library (joint angle presets for Pepper) ─────────
GESTURE_PRESETS = {
    "wave_hello": {
        "joints": ["RShoulderPitch", "RShoulderRoll",
                   "RElbowYaw",      "RElbowRoll"],
        "positions": [
            [-0.5,  0.2, 1.2, 0.8],   # raise arm
            [-0.3,  0.2, 1.2, 0.4],   # wave 1
            [-0.5,  0.2, 1.2, 0.8],   # wave 2
            [-0.3,  0.2, 1.2, 0.4],   # wave 3
        ],
        "durations": [0.8, 0.4, 0.4, 0.4],
    },
    "point_forward": {
        "joints": ["RShoulderPitch", "RShoulderRoll",
                   "RElbowYaw",      "RElbowRoll"],
        "positions": [[-0.5, -0.1, 1.5, 0.1]],
        "durations": [1.0],
    },
    "demonstrate": {
        "joints": ["HeadPitch", "HeadYaw"],
        "positions": [[0.2, 0.0], [0.2, 0.3],
                      [0.2, -0.3], [0.0, 0.0]],
        "durations": [0.5, 0.5, 0.5, 0.5],
    },
    "wave_goodbye": {
        "joints": ["RShoulderPitch", "RShoulderRoll",
                   "RElbowYaw",      "RElbowRoll"],
        "positions": [
            [-0.8, 0.4, 1.2, 1.0],
            [-0.8, 0.4, 1.2, 0.4],
            [-0.8, 0.4, 1.2, 1.0],
        ],
        "durations": [0.6, 0.4, 0.6],
    },
    "idle_animation": {
        "joints": ["HeadPitch", "HeadYaw"],
        "positions": [[0.05, 0.1], [0.05, -0.1], [0.0, 0.0]],
        "durations": [1.0, 1.0, 0.5],
    },
}

# ── LED colour mapping ────────────────────────────────────────
LED_MAP = {
    "green_flash":     {"color": "green",  "mode": "flash"},
    "blue_breathing":  {"color": "blue",   "mode": "breathing"},
    "yellow_solid":    {"color": "yellow", "mode": "solid"},
    "red_pulse":       {"color": "red",    "mode": "pulse"},
}


class RobotControllerNode(Node):

    def __init__(self):
        super().__init__("robot_controller_node")

        self.declare_parameter("robot_name", "pepper")
        self.declare_parameter("sim_mode",   True)

        self._sim = self.get_parameter("sim_mode").value

        # ── Subscribers ──────────────────────────────────────
        self.create_subscription(
            String, "/asd/robot_command",
            self._command_cb, 10)

        # ── Publishers ───────────────────────────────────────
        self._vel_pub = self.create_publisher(
            Twist, "/cmd_vel", 10)
        self._speech_pub = self.create_publisher(
            String, "/pepper/speech", 10)
        self._gesture_pub = self.create_publisher(
            String, "/pepper/gesture", 10)
        self._led_pub = self.create_publisher(
            String, "/pepper/led", 10)
        self._traj_pub = self.create_publisher(
            JointTrajectory,
            "/pepper_joint_trajectory_controller/joint_trajectory", 10)

        self.get_logger().info("RobotControllerNode ready ✔")

    # ── Command dispatcher ───────────────────────────────────
    def _command_cb(self, msg: String):
        try:
            cmd = json.loads(msg.data)
        except json.JSONDecodeError:
            return

        action  = cmd.get("action", "")
        payload = cmd.get("payload", "")

        dispatch = {
            "say":           self._do_say,
            "gesture":       self._do_gesture,
            "show_led":      self._do_led,
            "play_sound":    self._do_sound,
            "move_head":     self._do_head,
            "idle_animation":self._do_idle,
        }

        handler = dispatch.get(action)
        if handler:
            handler(payload)
        else:
            self.get_logger().warn(f"Unknown action: {action}")

    # ── Action implementations ───────────────────────────────
    def _do_say(self, text: str):
        self.get_logger().info(f"[TTS] → '{text}'")
        self._speech_pub.publish(String(data=text))

    def _do_gesture(self, gesture_name: str):
        preset = GESTURE_PRESETS.get(gesture_name)
        if not preset:
            self.get_logger().warn(f"Unknown gesture: {gesture_name}")
            return

        traj = JointTrajectory()
        traj.joint_names = preset["joints"]
        t_accum = 0.0

        for pos, dur in zip(preset["positions"], preset["durations"]):
            t_accum += dur
            pt = JointTrajectoryPoint()
            pt.positions = pos
            pt.time_from_start = Duration(
                sec=int(t_accum),
                nanosec=int((t_accum % 1) * 1e9)
            )
            traj.points.append(pt)

        self._traj_pub.publish(traj)
        self.get_logger().info(f"[GESTURE] → {gesture_name}")

    def _do_led(self, pattern: str):
        led_cmd = LED_MAP.get(pattern, {"color": "white", "mode": "solid"})
        self._led_pub.publish(String(data=json.dumps(led_cmd)))
        self.get_logger().info(f"[LED] → {pattern}")

    def _do_sound(self, filename: str):
        # In simulation: publish sound filename for Gazebo audio plugin
        self.get_logger().info(f"[SOUND] → {filename}")

    def _do_head(self, params):
        """Move Pepper head to target yaw/pitch."""
        if isinstance(params, dict):
            yaw   = float(params.get("yaw",   0.0))
            pitch = float(params.get("pitch", 0.0))
        else:
            yaw, pitch = 0.0, 0.0

        traj = JointTrajectory()
        traj.joint_names = ["HeadYaw", "HeadPitch"]
        pt = JointTrajectoryPoint()
        pt.positions = [yaw, pitch]
        pt.time_from_start = Duration(sec=1, nanosec=0)
        traj.points.append(pt)
        self._traj_pub.publish(traj)

    def _do_idle(self, _):
        self._do_gesture("idle_animation")


def main(args=None):
    rclpy.init(args=args)
    node = RobotControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
