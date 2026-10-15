# InternNav DualVLN on FiveAges W2

本仓库**不是** InternNav 的 fork。它记录并脚本化如何在 **W2-0035**（上半身 + Gemini 336L）与 **Linkhou S2** 底盘（RK3588）上运行 **InternVLA-N1 DualVLN**，推理在 GPU 工作站（**Sim-06**）上完成。

上游 InternNav：[InternRobotics/InternNav](https://github.com/InternRobotics/InternNav)

底盘栈（`s2_chassis_ws`）由底盘联调负责人维护。**除非对方要求，否则不要修改。** 本仓库仅按文档启动它。

## 硬件（实验室默认）

| 角色 | 主机 | IP | 登录 |
|------|------|-----|--------|
| DualVLN 服务端 | Sim-06 | `192.168.110.35` | `fiveages` |
| 上半身工控机 | W2-0035 | `192.168.111.223` | `fiveages` |
| 底盘 SBC | linux (3588) | `192.168.111.35` | `linux` / `linux` |

ROS 2 **Jazzy**，`RMW_IMPLEMENTATION=rmw_zenoh_cpp`，`ROS_DOMAIN_ID=0`。  
Zenoh **router** 在 W2-0035（`rmw_zenohd`）；底盘 Distrobox 是 `192.168.111.223:7447` 的 **client**。  
头部相机：**Orbbec Gemini 336L**（`CPC6463000WX`），话题 `/camera_head/color/image_raw`。  
**不要**在 W2-0035 上跑 DualVLN（RTX 4060，8 GB）。

## 文档

| 文件 | 用途 |
|------|-----|
| [`Quick_Start.md`](Quick_Start.md) | **仅运行时** — W2 Zenoh router、底盘 Distrobox（client + `publish_robot_state:=false`）、DualVLN、相机、dry-run / live |
| [`docs/Installation_Guide.md`](docs/Installation_Guide.md) | 克隆 InternNav、conda、DualVLN 权重、复制本仓库脚本 |
| [`docs/Architecture.md`](docs/Architecture.md) | 三机流水线、Zenoh 与 HTTP、动作码 |
| [`docs/W2_Implementation.md`](docs/W2_Implementation.md) | 相机、rqt、底盘 Distrobox、常见坑 |

## 脚本

| 路径 | 说明 |
|------|-------------|
| `scripts/internnav_w2_bridge.py` | W2 RGB → DualVLN HTTP → 可选 `/cmd_vel` |
| `scripts/save_head_rgb.py` | 无 GUI 保存一帧头部 RGB |

将 bridge 一次性拷到工控机：

```bash
scp scripts/internnav_w2_bridge.py fiveages@192.168.111.223:~/internnav_w2_bridge.py
```

## 快速开始

若 Sim-06 上已安装 InternNav + DualVLN，打开 [`Quick_Start.md`](Quick_Start.md)。

## 相关

Lift2S 使用另一套集成：`internnav_arx_lift2s`（RealSense + 不同 bridge）。不要与 H1 eval 混用端口（`h1_internvla_n1_async_cfg.py` 使用 **8023**）。本机上的 LightNav-0 是 **`~/LightNav-W2`**（WebSocket `:8051`，不是本 DualVLN 客户端）。单 GPU DualVLN 训练说明：[`docs/Fine_Tune_A6000.md`](docs/Fine_Tune_A6000.md)。


## Demo

[W2 DualVLN demo (mp4)](docs/media/InternNav-W2.mp4)
