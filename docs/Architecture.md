# Architecture — DualVLN on FiveAges W2

## 流水线

```
 language instruction
          │
          ▼
┌─────────────────────┐  HTTP :8087   ┌──────────────────────────┐
│ W2-0035             │ ◄───────────► │ Sim-06                   │
│ Gemini 336L         │  RGB + text   │ conda internnav          │
│ internnav_w2_bridge │  actions      │ DualVLN Agent Server     │
└─────────┬───────────┘               └──────────────────────────┘
          │ /cmd_vel
          │ Zenoh :7447  ROS_DOMAIN_ID=0
          ▼
┌─────────────────────┐
│ 3588 Distrobox      │
│ s2_chassis_ws       │
│ Linkhou S2 wheels   │
└─────────────────────┘
```

| 路径 | 传输 |
|------|-----------|
| 相机 → bridge | W2 上的 ROS 2（`/camera_head/color/image_raw`） |
| 底盘 ↔ W2 | ROS 2 Zenoh（`/cmd_vel`、`/chassis/odom`、`/chassis/joint_states`、…） |
| W2 ↔ DualVLN | HTTP 到 Sim-06 `:8087`（不是 Zenoh） |

Sim-06 **不**加入机器人 ROS 图。不要在 4060 上加载 DualVLN。

## 离散动作

| 码 | 名称 | Bridge |
|------|------|--------|
| 0 | STOP | 零 Twist |
| 1 | FORWARD | `linear.x` |
| 2 | TURN_LEFT | `+angular.z` |
| 3 | TURN_RIGHT | `-angular.z` |
| -1 / 5 | LOOK_DOWN / WAIT | 仅停车（**不**动头部） |

机器人停着做 dry-run **不能**证明目标搜索：图像不会变。请在 live 闭环上判断导航。

## Zenoh

**Router：** W2-0035，`ros2 run rmw_zenoh_cpp rmw_zenohd`，通常为 `tcp/192.168.111.223:7447`。在底盘 launch **之前**启动。相机 launch 应挂到已有 router（`Detected running rmw_zenohd`）。

**Client：** 3588 Distrobox。`ZENOH_CONFIG_OVERRIDE` 必须为 `mode="client";connect/endpoints=["tcp/192.168.111.223:7447"]`（`CHASSIS_ZENOH_REMOTE=1` / `s2_chassis_ws` 环境文件）。Launch 使用 `publish_robot_state:=false`。

7447 上两个 `rmw_zenohd` 会失败或分裂图。不要在底盘上 `unset ZENOH_CONFIG_OVERRIDE`。

H1 Docker eval 使用**另一套** InternNav 配置与端口 **8023**。Lift2S / W2 DualVLN 仍用 **8087**。
