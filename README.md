# InternNav DualVLN on FiveAges W2

本仓库**不是** InternNav 的 fork。它记录并脚本化如何在 **W2-019**（上半身 + Gemini 336L）与 **Linkhou S2** 底盘（RK3588）上运行 **InternVLA-N1 DualVLN**，推理在 GPU 工作站（**zy**）上完成。

上游 InternNav：[InternRobotics/InternNav](https://github.com/InternRobotics/InternNav)

底盘栈（`s2_chassis_ws`）由底盘负责人维护。**除非对方要求，不要改它。** 本仓库只按文档启动。

## 硬件（实验室默认 / W2-019）

| 角色 | 主机 | IP | 登录 |
|------|------|-----|------|
| DualVLN 服务端 | zy | `192.168.110.35` | `fiveages` |
| 上半身工控机 | W2-019 | `192.168.110.69`（Wi‑Fi；有线常见 `6.6.6.100`） | `fiveages` / `123456` |
| 底盘 SBC | linux（3588） | 按现场（例：`192.168.111.61`） | `linux` / `linux` |

ROS 2 **Jazzy**，`RMW_IMPLEMENTATION=rmw_zenoh_cpp`，`ROS_DOMAIN_ID=0`。  
Zenoh **router** 在 W2-019（`rmw_zenohd`）；底盘 Distrobox 是该 W2 router（例：`tcp/192.168.110.69:7447`）的 **client**。  
头部相机：**Orbbec Gemini 336L**（W2-019：`CPC9363000CZ`），话题 `/camera_head/color/image_raw`。  
**不要**在 W2 上跑 DualVLN（板载 GPU 显存不够）。

## 文档

| 文件 | 用途 |
|------|------|
| [`Quick_Start.md`](Quick_Start.md) | **仅运行时** — Zenoh router、底盘 Distrobox、DualVLN、相机、dry-run / live（含 SocialGen） |
| [`docs/Installation_Guide.md`](docs/Installation_Guide.md) | 克隆 InternNav、**uv** 环境、DualVLN + SocialGen 权重、复制本仓库脚本 |
| [`docs/Architecture.md`](docs/Architecture.md) | 三机流水线、Zenoh vs HTTP、动作码 |
| [`docs/W2_Implementation.md`](docs/W2_Implementation.md) | 相机、rqt、底盘 Distrobox、坑点 |

## 脚本

| 路径 | 说明 |
|------|------|
| `scripts/internnav_w2_bridge.py` | W2 RGB → DualVLN HTTP → 可选 `/cmd_vel` |
| `scripts/save_head_rgb.py` | 无 GUI 保存一帧头部 RGB |

将 bridge 拷到工控机一次：

```bash
scp scripts/internnav_w2_bridge.py fiveages@192.168.110.69:~/internnav_w2_bridge.py
```

## 快速开始

若 zy 上已装好 InternNav + DualVLN（uv `.venv`），打开 [`Quick_Start.md`](Quick_Start.md)。

## 相关

Lift2S 另有集成：`internnav_arx_lift2s`（RealSense + 不同 bridge）。不要与 H1 eval 端口混用（`h1_internvla_n1_async_cfg.py` 用 **8023**）。本机 LightNav-0 是 **`~/LightNav-W2`**（WebSocket `:8051`，不是本 DualVLN 客户端）。

## Demo

[W2 DualVLN demo (mp4)](docs/media/InternNav-W2.mp4)
