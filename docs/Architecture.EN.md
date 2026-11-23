# Architecture — DualVLN on FiveAges W2

## Pipeline

```
 language instruction
          │
          ▼
┌─────────────────────┐  HTTP :8087   ┌──────────────────────────┐
│ W2-019             │ ◄───────────► │ zy                   │
│ Gemini 336L         │  RGB + text   │ uv .venv (InternNav)    │
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

| Path | Transport |
|------|-----------|
| Camera → bridge | ROS 2 on W2 (`/camera_head/color/image_raw`) |
| Chassis ↔ W2 | ROS 2 Zenoh (`/cmd_vel`, `/chassis/odom`, `/chassis/joint_states`, …) |
| W2 ↔ DualVLN | HTTP to zy `:8087` (not Zenoh) |

zy does **not** join the robot ROS graph. Do not load DualVLN on the 4060.

## Discrete actions

| Code | Name | Bridge |
|------|------|--------|
| 0 | STOP | zero Twist |
| 1 | FORWARD | `linear.x` |
| 2 | TURN_LEFT | `+angular.z` |
| 3 | TURN_RIGHT | `-angular.z` |
| -1 / 5 | LOOK_DOWN / WAIT | stop only (head is **not** moved) |

Dry-run with a parked robot does **not** prove object search: the image never changes. Judge navigation on a live closed loop.

## Zenoh

**Router:** W2-019, `ros2 run rmw_zenoh_cpp rmw_zenohd`, typically `tcp/192.168.110.69:7447`. Start this **before** the chassis launch. The camera launch should attach to the existing router (`Detected running rmw_zenohd`).

**Client:** 3588 Distrobox. `ZENOH_CONFIG_OVERRIDE` must be `mode="client";connect/endpoints=["tcp/192.168.110.69:7447"]` (`CHASSIS_ZENOH_REMOTE=1` / `s2_chassis_ws` env files). Launch with `publish_robot_state:=false`.

Two `rmw_zenohd` instances on 7447 will fail or split the graph. Do not `unset ZENOH_CONFIG_OVERRIDE` on the chassis.

H1 Docker eval uses a **different** InternNav config and port **8023**. Lift2S / W2 DualVLN stay on **8087**.
