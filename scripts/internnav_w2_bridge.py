#!/usr/bin/env python3
"""W2 ROS bridge to InternNav DualVLN (Phase E).

Subscribes to /head_camera/rgb, sends RGB + a language instruction to the
InternNav AgentClient (server on localhost:8087), and executes discrete
actions on /cmd_vel:

  0 stop | 1 forward ~0.25 m | 2 turn left ~15 deg | 3 turn right ~15 deg

Does not use YOLO. Does not query Isaac prim poses.
Dummy depth is used (DualVLN is RGB; the agent still indexes depth[:,:,0]).

ROS 2 Jazzy rclpy is Python 3.12. InternNav uv venv is Python 3.10. Do NOT
import rclpy inside internnav — this script talks to the InternNav server
over HTTP, so it can run in the same 3.12 venv as detect_apple.py.

On W2-019 (ROS 2 Jazzy, not InternNav uv venv):

  python3 ~/internnav_w2_bridge.py \\
    --host 192.168.110.35 --rgb-topic /camera_head/color/image_raw \\
    --no-use-sim-time --no-tuck --dry-run \\
    --instruction "walk forward and find the black dustbin on the floor"
"""

from __future__ import annotations

import argparse
import base64
import json
import pickle
import sys
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

import numpy as np
import rclpy
from geometry_msgs.msg import Twist
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image, JointState
from std_msgs.msg import Int32

# OCS2 home_1 (same numbers as detect_apple.py / fa-w2-description common.yaml).
_ARM_HOME: Dict[str, float] = {
    "left_joint1": 1.457133809892805,
    "left_joint2": -1.0633699963902674,
    "left_joint3": -1.1994065285584414,
    "left_joint4": -0.8074199090303408,
    "left_joint5": -0.6949558811978124,
    "left_joint6": -0.6864381599253574,
    "left_joint7": -0.1295225067208675,
    "right_joint1": -1.457133809892805,
    "right_joint2": -1.0633699963902674,
    "right_joint3": 1.1994065285584414,
    "right_joint4": -0.8074199090303408,
    "right_joint5": 0.6949558811978124,
    "right_joint6": -0.6864381599253574,
    "right_joint7": 0.1295225067208675,
}
_BODY_HOME: Dict[str, float] = {
    "body_joint1": -0.9,
    "body_joint2": -1.8,
    "body_joint3": -0.9,
    "body_joint4": 0.0,
}
_FSM_HOME = 1
_ACTION_NAMES = {
    0: "STOP",
    1: "FORWARD",
    2: "TURN_LEFT",
    3: "TURN_RIGHT",
    -1: "WAIT/LOOK_DOWN",
    5: "LOOK_DOWN",
}


def _qos() -> QoSProfile:
    return QoSProfile(
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.VOLATILE,
        history=HistoryPolicy.KEEP_LAST,
        depth=5,
    )


def imgmsg_to_rgb(msg: Image) -> np.ndarray:
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
    if enc == "bgr8":
        img = img[:, :, ::-1]
    return np.ascontiguousarray(img)


def parse_action(raw: Any) -> int:
    """Unwrap AgentClient / internvla_n1_agent return shapes to one int."""
    x = raw
    if isinstance(x, list) and x and isinstance(x[0], dict) and "action" in x[0]:
        x = x[0]["action"]
    if isinstance(x, dict) and "action" in x:
        x = x["action"]
    while isinstance(x, (list, tuple)) and len(x) == 1:
        x = x[0]
    if isinstance(x, (list, tuple)) and x:
        x = x[0]
    return int(x)


def _smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


class W2InternNavBridge(Node):
    def __init__(
        self,
        instruction: str,
        width: int,
        height: int,
        lin_x: float,
        yaw_rate: float,
        forward_m: float,
        turn_deg: float,
        dummy_depth_m: float,
        tuck: bool,
        tuck_body: bool,
        tuck_duration: float,
        dry_run: bool,
        rgb_topic: str = "/head_camera/rgb",
        use_sim_time: bool = True,
    ) -> None:
        super().__init__("internnav_w2_bridge")
        self.set_parameters(
            [Parameter("use_sim_time", Parameter.Type.BOOL, use_sim_time)]
        )
        self._instruction = instruction
        self._width = width
        self._height = height
        self._lin_x = lin_x
        self._yaw_rate = yaw_rate
        self._forward_m = forward_m
        self._turn_deg = turn_deg
        self._dummy_depth_m = dummy_depth_m
        self._dry_run = dry_run
        self._rgb_topic = rgb_topic
        self._lock = threading.Lock()
        self._latest_rgb: Optional[np.ndarray] = None
        self._latest_js: Optional[JointState] = None
        self._frames = 0

        self._cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self._fsm_pub = self.create_publisher(Int32, "/fsm_command", 10)
        self._joint_cmd_pub = self.create_publisher(JointState, "/isaac/joint_command", 10)
        self.create_subscription(Image, rgb_topic, self._on_image, _qos())
        self.create_subscription(JointState, "/isaac/joint_states", self._on_js, _qos())
        self.create_subscription(JointState, "/joint_states", self._on_js, _qos())
        self.create_timer(5.0, self._watchdog)

        self._tuck = tuck
        self._tuck_duration = tuck_duration
        self._home = dict(_ARM_HOME)
        # Never apply OCS2 waist home_1 without the WBC: those angles fold the
        # torso over the rear of the chassis and the wheeled base tips over.
        if tuck_body:
            self._home.update(_BODY_HOME)

        self.get_logger().info(
            f"InternNav W2 bridge: instruction={instruction!r} "
            f"rgb={width}x{height} topic={rgb_topic} sim_time={use_sim_time} "
            f"dry_run={dry_run}"
        )

    def _on_image(self, msg: Image) -> None:
        try:
            rgb = imgmsg_to_rgb(msg)
        except ValueError as exc:
            self.get_logger().warn(str(exc))
            return
        if rgb.shape[1] != self._width or rgb.shape[0] != self._height:
            import cv2

            rgb = cv2.resize(rgb, (self._width, self._height), interpolation=cv2.INTER_AREA)
        with self._lock:
            self._latest_rgb = rgb
            self._frames += 1

    def _on_js(self, msg: JointState) -> None:
        if msg.name and msg.position:
            self._latest_js = msg

    def _watchdog(self) -> None:
        if self._frames == 0:
            self.get_logger().warn(
                f"No {self._rgb_topic} yet. Same RMW/DOMAIN as the camera; "
                "on Isaac, Play must be ON."
            )

    def wait_for_rgb(self, timeout_s: float = 30.0) -> np.ndarray:
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            with self._lock:
                if self._latest_rgb is not None:
                    return self._latest_rgb.copy()
            time.sleep(0.05)
        raise TimeoutError(f"Timed out waiting for {self._rgb_topic}")

    def current_obs(self) -> Dict[str, Any]:
        with self._lock:
            if self._latest_rgb is None:
                raise RuntimeError("no rgb")
            rgb = self._latest_rgb.copy()
        h, w = rgb.shape[:2]
        # Agent uses depth[:,:,0]. DualVLN is RGB; fill a constant metric plane.
        depth_u8 = np.full((h, w, 1), int(np.clip(self._dummy_depth_m * 25.5, 1, 255)), np.uint8)
        return {
            "rgb": rgb,
            "depth": depth_u8,
            "instruction": self._instruction,
        }

    def stop(self) -> None:
        self._cmd_pub.publish(Twist())

    def execute_action(self, action: int) -> None:
        name = _ACTION_NAMES.get(action, f"UNKNOWN({action})")
        self.get_logger().info(f"InternNav action={action} ({name})")
        if self._dry_run or action in (-1, 0, 5):
            self.stop()
            return
        twist = Twist()
        duration = 0.4
        if action == 1:
            twist.linear.x = self._lin_x
            duration = abs(self._forward_m / max(self._lin_x, 1e-3))
        elif action == 2:
            twist.angular.z = abs(self._yaw_rate)
            duration = abs(np.deg2rad(self._turn_deg) / max(self._yaw_rate, 1e-3))
        elif action == 3:
            twist.angular.z = -abs(self._yaw_rate)
            duration = abs(np.deg2rad(self._turn_deg) / max(self._yaw_rate, 1e-3))
        else:
            self.get_logger().warn(f"Unmapped action {action}; stopping.")
            self.stop()
            return
        duration = float(np.clip(duration, 0.2, 3.0))
        t_end = time.time() + duration
        while time.time() < t_end and rclpy.ok():
            self._cmd_pub.publish(twist)
            time.sleep(0.05)
        self.stop()

    def tuck_arms(self) -> None:
        if not self._tuck:
            return
        n_sub = 0
        try:
            n_sub = self.count_subscribers("/fsm_command")
        except Exception:
            n_sub = 0
        if n_sub > 0:
            msg = Int32()
            msg.data = _FSM_HOME
            self._fsm_pub.publish(msg)
            self.get_logger().info(
                f"Tuck: /fsm_command={_FSM_HOME} (HOME), wait {self._tuck_duration:.1f}s"
            )
            time.sleep(self._tuck_duration)
            return
        self.get_logger().info(
            f"Tuck: no OCS2; interpolating /isaac/joint_command for {self._tuck_duration:.1f}s"
        )
        start: Dict[str, float] = {}
        if self._latest_js is not None:
            for n, p in zip(self._latest_js.name, self._latest_js.position):
                if n in self._home:
                    start[n] = float(p)
        for n in self._home:
            start.setdefault(n, 0.0)
        t0 = time.time()
        while True:
            elapsed = time.time() - t0
            alpha = _smoothstep(elapsed / max(self._tuck_duration, 0.5))
            cmd = JointState()
            cmd.header.stamp = self.get_clock().now().to_msg()
            cmd.name = list(self._home.keys())
            cmd.position = [
                start[n] + alpha * (self._home[n] - start[n]) for n in cmd.name
            ]
            self._joint_cmd_pub.publish(cmd)
            if elapsed >= self._tuck_duration:
                break
            time.sleep(0.05)
        self.get_logger().info("Tuck complete.")


def _agent_settings(model_path: str, device: str) -> Dict[str, Any]:
    return {
        "policy_name": "InternVLAN1_Policy",
        "state_encoder": None,
        "env_num": 1,
        "sim_num": 1,
        "model_path": model_path,
        "camera_intrinsic": [[585.0, 0.0, 320.0], [0.0, 585.0, 240.0], [0.0, 0.0, 1.0]],
        "width": 640,
        "height": 480,
        "hfov": 79,
        "resize_w": 384,
        "resize_h": 384,
        "max_new_tokens": 1024,
        "num_frames": 32,
        "num_history": 8,
        "num_future_steps": 4,
        "device": device,
        "predict_step_nums": 32,
        "continuous_traj": True,
        "infer_mode": "partial_async",
        "vis_debug": False,
    }


class InternNavHttpClient:
    """Same protocol as internnav.utils.AgentClient, without importing internnav.

    Jazzy rclpy is CPython 3.12; InternNav uv venv is 3.10. DualVLN stays in
    the internnav process (start_server.py).
    """

    def __init__(self, host: str, port: int, model_path: str, device: str) -> None:
        self.base = f"http://{host}:{port}"
        payload = {
            "agent_config": {
                "server_host": host,
                "server_port": port,
                "model_name": "internvla_n1",
                "ckpt_path": "",
                "model_settings": _agent_settings(model_path, device),
            }
        }
        data = self._post("/agent/init", payload)
        self.agent_name = data["agent_name"]

    def _post(self, path: str, body: Dict[str, Any]) -> Any:
        req = urllib.request.Request(
            self.base + path,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:800]
            raise RuntimeError(
                f"InternNav HTTP {path} failed ({exc.code} {exc.reason}). {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"InternNav HTTP {path} failed ({exc}). "
                "Is `python scripts/eval/start_server.py --port 8087` running "
                "in the internnav env?"
            ) from exc

    def step(self, obs: list) -> Any:
        encoded = base64.b64encode(pickle.dumps(obs)).decode("utf-8")
        data = self._post(f"/agent/{self.agent_name}/step", {"observation": encoded})
        return data["action"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--instruction",
        default="find the apple on the table",
        help="Language goal sent with every InternNav step.",
    )
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8087)
    parser.add_argument(
        "--model-path",
        default="checkpoints/InternVLA-N1-DualVLN",
        help="Path relative to InternNav cwd on zy (e.g. checkpoints/InternVLA-N1-DualVLN or ...-SocialGen-10k-3ep-20261115).",
    )
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--lin-x", type=float, default=0.20)
    parser.add_argument("--yaw-rate", type=float, default=0.25)
    parser.add_argument("--forward-m", type=float, default=0.20)
    parser.add_argument("--turn-deg", type=float, default=10.0)
    parser.add_argument(
        "--tuck-body",
        action="store_true",
        help="Also command OCS2 waist home_1 (unsafe without WBC — tips W2).",
    )
    parser.add_argument("--dummy-depth-m", type=float, default=1.5)
    parser.add_argument("--max-steps", type=int, default=80)
    parser.add_argument("--step-pause", type=float, default=0.15)
    parser.add_argument("--no-tuck", action="store_true")
    parser.add_argument("--tuck-duration", type=float, default=5.0)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Call InternNav and log actions; do not publish /cmd_vel motion.",
    )
    parser.add_argument(
        "--rgb-topic",
        default="/head_camera/rgb",
        help="RGB Image topic (Isaac: /head_camera/rgb; real W2: /camera_head/color/image_raw).",
    )
    parser.add_argument(
        "--use-sim-time",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="True for Isaac. Pass --no-use-sim-time on the real robot.",
    )
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    args, ros_args = parser.parse_known_args()

    rclpy.init(args=ros_args)
    node = W2InternNavBridge(
        instruction=args.instruction,
        width=args.width,
        height=args.height,
        lin_x=args.lin_x,
        yaw_rate=args.yaw_rate,
        forward_m=args.forward_m,
        turn_deg=args.turn_deg,
        dummy_depth_m=args.dummy_depth_m,
        tuck=not args.no_tuck,
        tuck_body=args.tuck_body,
        tuck_duration=args.tuck_duration,
        dry_run=args.dry_run,
        rgb_topic=args.rgb_topic,
        use_sim_time=args.use_sim_time,
    )
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    try:
        node.get_logger().info("Waiting for /head_camera/rgb …")
        node.wait_for_rgb(timeout_s=45.0)
        node.tuck_arms()

        node.get_logger().info(
            f"Connecting to InternNav HTTP {args.host}:{args.port} "
            "(server process stays in InternNav uv venv / Python 3.10)."
        )
        agent = InternNavHttpClient(
            args.host, args.port, args.model_path, args.device
        )
        node.get_logger().info("InternNav init OK — starting VLN steps.")

        for i in range(args.max_steps):
            if not rclpy.ok():
                break
            obs = node.current_obs()
            t0 = time.time()
            raw = agent.step([obs])
            dt = time.time() - t0
            action = parse_action(raw)
            node.get_logger().info(
                f"step {i + 1}/{args.max_steps}  infer={dt:.1f}s  raw={raw!r}"
            )
            node.execute_action(action)
            if action == 0:
                node.get_logger().info("InternNav returned STOP — ending loop.")
                break
            time.sleep(args.step_pause)
    except KeyboardInterrupt:
        pass
    except TimeoutError as exc:
        node.get_logger().error(str(exc))
        sys.exit(1)
    finally:
        node.stop()
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
