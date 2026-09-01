#!/usr/bin/env python3
"""Save one head RGB frame (no GUI). Run on W2-0035 with the camera launch up."""

from __future__ import annotations

import argparse
import sys

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image


def imgmsg_to_bgr(msg: Image) -> np.ndarray:
    enc = (msg.encoding or "").lower()
    if enc not in ("rgb8", "bgr8", "rgba8", "bgra8"):
        raise ValueError(f"Unsupported encoding {msg.encoding!r}")
    channels = 4 if enc.endswith("a8") else 3
    row_bytes = msg.width * channels
    buf = np.frombuffer(msg.data, dtype=np.uint8)
    if msg.step == row_bytes:
        img = buf.reshape(msg.height, msg.width, channels)
    else:
        img = buf.reshape(msg.height, msg.step)[:, :row_bytes].reshape(
            msg.height, msg.width, channels
        )
    if channels == 4:
        img = img[:, :, :3]
        enc = "rgb8" if enc.startswith("rgb") else "bgr8"
    if enc == "rgb8":
        img = img[:, :, ::-1]
    return np.ascontiguousarray(img)


class Saver(Node):
    def __init__(self, topic: str, out: str) -> None:
        super().__init__("save_head_rgb")
        self._out = out
        self._done = False
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        )
        self.create_subscription(Image, topic, self._cb, qos)

    def _cb(self, msg: Image) -> None:
        if self._done:
            return
        import cv2

        bgr = imgmsg_to_bgr(msg)
        cv2.imwrite(self._out, bgr)
        self.get_logger().info(f"Wrote {self._out} ({msg.width}x{msg.height} {msg.encoding})")
        self._done = True


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--topic", default="/camera_head/color/image_raw")
    p.add_argument("--out", default="/tmp/w2_head_rgb.png")
    p.add_argument("--timeout", type=float, default=10.0)
    args, ros_args = p.parse_known_args()
    rclpy.init(args=ros_args)
    node = Saver(args.topic, args.out)
    t0 = node.get_clock().now()
    while rclpy.ok() and not node._done:
        rclpy.spin_once(node, timeout_sec=0.1)
        if (node.get_clock().now() - t0).nanoseconds / 1e9 > args.timeout:
            node.get_logger().error(f"No image on {args.topic} within {args.timeout}s")
            sys.exit(1)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
