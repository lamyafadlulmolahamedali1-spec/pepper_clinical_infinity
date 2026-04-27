#!/usr/bin/env python3
"""
sensor_fusion_node.py
─────────────────────
Subscribes to raw perception outputs and produces a unified
ChildState estimate used by the Therapeutic Interaction Engine.

Subscribes:
  /asd/perception/detections      (vision_msgs/Detection2DArray)
  /asd/perception/child_emotion   (std_msgs/String  JSON)
  /asd/perception/activity        (std_msgs/String)

Publishes:
  /asd/child_state                (std_msgs/String  JSON)
    {
      "emotion":       "happy",
      "emotion_conf":  0.82,
      "activity":      "playing_with_toy",
      "child_present": true,
      "timestamp":     1234567890.123
    }
"""

import json
import collections
import rclpy
from rclpy.node import Node
from rclpy.time import Time

from std_msgs.msg import String
from vision_msgs.msg import Detection2DArray


class SensorFusionNode(Node):

    def __init__(self):
        super().__init__("sensor_fusion_node")

        # ── Parameters ───────────────────────────────────────
        self.declare_parameter("fusion_rate_hz", 10)
        self.declare_parameter("emotion_smoothing_window", 5)
        self.declare_parameter("activity_confidence_threshold", 0.6)

        rate    = self.get_parameter("fusion_rate_hz").value
        win     = self.get_parameter("emotion_smoothing_window").value

        # ── State buffers ─────────────────────────────────────
        self._emotion_buffer  = collections.deque(maxlen=win)
        self._emotion_scores  = {}
        self._activity        = "unknown"
        self._child_present   = False

        # ── Subscribers ──────────────────────────────────────
        self.create_subscription(
            Detection2DArray, "/asd/perception/detections",
            self._det_cb, 10)
        self.create_subscription(
            String, "/asd/perception/child_emotion",
            self._emotion_cb, 10)
        self.create_subscription(
            String, "/asd/perception/activity",
            self._activity_cb, 10)

        # ── Publisher ─────────────────────────────────────────
        self._state_pub = self.create_publisher(
            String, "/asd/child_state", 10)

        # ── Timer ─────────────────────────────────────────────
        self.create_timer(1.0 / rate, self._publish_state)

        self.get_logger().info("SensorFusionNode ready ✔")

    def _det_cb(self, msg: Detection2DArray):
        for det in msg.detections:
            for hyp in det.results:
                if hyp.hypothesis.class_id == "person":
                    self._child_present = True
                    return
        self._child_present = False

    def _emotion_cb(self, msg: String):
        try:
            data = json.loads(msg.data)
            self._emotion_buffer.append(data.get("dominant", "neutral"))
            self._emotion_scores = data.get("scores", {})
        except json.JSONDecodeError:
            pass

    def _activity_cb(self, msg: String):
        self._activity = msg.data

    def _publish_state(self):
        # ── Majority-vote smoothing ───────────────────────────
        if self._emotion_buffer:
            counts = collections.Counter(self._emotion_buffer)
            dominant, count = counts.most_common(1)[0]
            confidence = count / len(self._emotion_buffer)
        else:
            dominant, confidence = "neutral", 1.0

        state = {
            "emotion":       dominant,
            "emotion_conf":  round(confidence, 3),
            "activity":      self._activity,
            "child_present": self._child_present,
            "timestamp":     self.get_clock().now().nanoseconds / 1e9,
        }

        self._state_pub.publish(String(data=json.dumps(state)))


def main(args=None):
    rclpy.init(args=args)
    node = SensorFusionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
