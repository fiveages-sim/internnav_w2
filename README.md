# InternNav DualVLN on FiveAges W2

This repository is **not** a fork of InternNav. It documents and scripts how to run **InternVLA-N1 DualVLN** on **W2-0035** (upper body + Gemini 336L) and the **Linkhou S2** chassis (RK3588), with inference on a GPU workstation (**Sim-06**).

Upstream InternNav: [InternRobotics/InternNav](https://github.com/InternRobotics/InternNav)

Chassis stack (`s2_chassis_ws`) is owned by the chassis bring-up owner. **Do not edit it** unless they ask. This repo only launches it as documented.

## Hardware (lab defaults)

| Role | Host | IP | Login |
|------|------|-----|--------|
| DualVLN server | Sim-06 | `192.168.110.35` | `fiveages` |
| Upper body IPC | W2-0035 | `192.168.111.223` | `fiveages` |
| Chassis SBC | linux (3588) | `192.168.111.35` | `linux` / `linux` |

ROS 2 **Jazzy**, `RMW_IMPLEMENTATION=rmw_zenoh_cpp`, `ROS_DOMAIN_ID=0`.  
Head camera: **Orbbec Gemini 336L** (`CPC6463000WX`), topic `/camera_head/color/image_raw`.  
Do **not** run DualVLN on W2-0035 (RTX 4060, 8 GB).

## Documents

| File | Use |
|------|-----|
| [`Quick_Start.md`](Quick_Start.md) | **Runtime only** — SSH, chassis launch, DualVLN server, camera, dry-run / live |
| [`docs/Installation_Guide.md`](docs/Installation_Guide.md) | Clone InternNav, conda, DualVLN weights, copy this repo’s scripts |
| [`docs/Architecture.md`](docs/Architecture.md) | Three-machine pipeline, Zenoh vs HTTP, action codes |
| [`docs/W2_Implementation.md`](docs/W2_Implementation.md) | Camera, rqt, chassis Distrobox, pitfalls |

## Scripts

| Path | Description |
|------|-------------|
| `scripts/internnav_w2_bridge.py` | W2 RGB → DualVLN HTTP → optional `/cmd_vel` |
| `scripts/save_head_rgb.py` | Save one head RGB frame without a GUI |

Copy the bridge onto the IPC once:

```bash
scp scripts/internnav_w2_bridge.py fiveages@192.168.111.223:~/internnav_w2_bridge.py
```

## Quick start

If InternNav + DualVLN are already installed on Sim-06, open [`Quick_Start.md`](Quick_Start.md).

## Related

Lift2S uses a separate integration: `internnav_arx_lift2s` (RealSense + different bridge). Do not mix ports with H1 eval (`h1_internvla_n1_async_cfg.py` uses **8023**). LightNav-0 is a different model (`~/LightNav-0`).
