# Installation — InternNav DualVLN for W2

Clone and weights go on **Sim-06 only**. W2-0035 needs ROS 2 Jazzy, `orbbec_camera` (`~/ros2_ws`), and a copy of `internnav_w2_bridge.py`. The 3588 already has `s2_chassis_ws` (do not modify).

Upstream: [InternRobotics/InternNav](https://github.com/InternRobotics/InternNav)

## 1. Clone InternNav (Sim-06)

China: GitHub often needs a proxy or `gitclone.com` / `ghproxy` (see lab FlyingBird notes). Example:

```bash
cd ~
git clone --depth 1 https://github.com/InternRobotics/InternNav.git ~/InternNav
# if that times out:
# git clone --depth 1 https://gitclone.com/github.com/InternRobotics/InternNav.git ~/InternNav
```

Do **not** clone InternNav onto W2-0035 or the 3588 for inference.

## 2. Conda env and DualVLN weights (Sim-06)

```bash
conda create -n internnav python=3.10 -y
conda activate internnav
cd ~/InternNav
# Follow InternNav README / this lab’s InternNav_clone_to_5090_commands.md
# Pin huggingface_hub for transformers 4.51 (do not blindly upgrade to hub 1.x).
```

Weights (China mirror):

```bash
conda activate internnav
export HF_ENDPOINT=https://hf-mirror.com
export HF_HUB_DISABLE_XET=1
mkdir -p ~/InternNav/checkpoints
huggingface-cli download InternRobotics/InternVLA-N1-DualVLN \
  --local-dir ~/InternNav/checkpoints/InternVLA-N1-DualVLN
```

Expect shards under `checkpoints/InternVLA-N1-DualVLN/`. VLN-CE / InternData-N1 is **not** required for W2 real-robot inference.

## 3. This repository

```bash
# after you clone InternNav-W2 (this repo) onto Sim-06, e.g. ~/InternNav-W2
scp ~/InternNav-W2/scripts/internnav_w2_bridge.py fiveages@192.168.111.223:~/internnav_w2_bridge.py
scp ~/InternNav-W2/scripts/save_head_rgb.py fiveages@192.168.111.223:~/save_head_rgb.py
```

W2 Python is system **3.12** + ROS `rclpy`. Do not `pip install internnav` into that interpreter.

## 4. W2 camera package

On W2-0035, `~/ros2_ws` must provide `orbbec_camera` and launch file `gemini_330_series_head.launch.py`. Overlay:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
```

## 5. Chassis

On `192.168.111.35`, Distrobox `ubuntu24` and `~/s2_chassis_ws` must already be built by the chassis owner. This repo does not install them.

## 6. LAN HTTP

If a system proxy blocks `:8087`:

```bash
export NO_PROXY="192.168.110.35,localhost,127.0.0.1"
export no_proxy="$NO_PROXY"
```

Next: [`../Quick_Start.md`](../Quick_Start.md).
