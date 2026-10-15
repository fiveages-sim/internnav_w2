# Installation — InternNav DualVLN for W2

克隆与权重只放在 **Sim-06**。W2-0035 需要 ROS 2 Jazzy、`orbbec_camera`（`~/ros2_ws`），以及一份 `internnav_w2_bridge.py`。3588 已有 `s2_chassis_ws`（不要改）。

上游：[InternRobotics/InternNav](https://github.com/InternRobotics/InternNav)

## 1. 克隆 InternNav（Sim-06）

国内：GitHub 常需代理或 `gitclone.com` / `ghproxy`（见实验室 FlyingBird 说明）。示例：

```bash
cd ~
git clone --depth 1 https://github.com/InternRobotics/InternNav.git ~/InternNav
# 若超时：
# git clone --depth 1 https://gitclone.com/github.com/InternRobotics/InternNav.git ~/InternNav
```

**不要**为了推理把 InternNav 克隆到 W2-0035 或 3588。

## 2. Conda 环境与 DualVLN 权重（Sim-06）

```bash
conda create -n internnav python=3.10 -y
conda activate internnav
cd ~/InternNav
# 按 InternNav README / 本实验室 InternNav_clone_to_5090_commands.md 操作
# 为 transformers 4.51 固定 huggingface_hub（勿盲目升级到 hub 1.x）。
```


权重（国内镜像）：

```bash
conda activate internnav
export HF_ENDPOINT=https://hf-mirror.com
export HF_HUB_DISABLE_XET=1
mkdir -p ~/InternNav/checkpoints
huggingface-cli download InternRobotics/InternVLA-N1-DualVLN \
  --local-dir ~/InternNav/checkpoints/InternVLA-N1-DualVLN
```

期望在 `checkpoints/InternVLA-N1-DualVLN/` 下看到分片。W2 真机推理**不需要** VLN-CE / InternData-N1。

## 3. 本仓库

```bash
# 将 InternNav-W2（本仓库）克隆到 Sim-06 后，例如 ~/InternNav-W2
scp ~/InternNav-W2/scripts/internnav_w2_bridge.py fiveages@192.168.111.223:~/internnav_w2_bridge.py
scp ~/InternNav-W2/scripts/save_head_rgb.py fiveages@192.168.111.223:~/save_head_rgb.py
```


W2 的 Python 是系统 **3.12** + ROS `rclpy`。不要往该解释器里 `pip install internnav`。

## 4. W2 相机包

在 W2-0035 上，`~/ros2_ws` 须提供 `orbbec_camera` 与 launch 文件 `gemini_330_series_head.launch.py`。叠加环境：

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
```

## 5. 底盘

在 `192.168.111.61` 上，Distrobox `ubuntu24` 与 `~/s2_chassis_ws` 须已由底盘负责人编好。本仓库不安装它们。

运行时（见 [`../Quick_Start.md`](../Quick_Start.md)）：先在 W2-0035 启动 `rmw_zenohd`。在 Distrobox 中，`ZENOH_CONFIG_OVERRIDE` 须指向 `tcp/192.168.111.223:7447`，然后：

```bash
ros2 launch linkhou_s2_description chassis_ros2_control.launch.py \
  can_iface:=bcan0 publish_robot_state:=false
```

## 6. 局域网 HTTP

若系统代理挡住 `:8087`：

```bash
export NO_PROXY="192.168.110.35,localhost,127.0.0.1"
export no_proxy="$NO_PROXY"
```

下一步：[`../Quick_Start.md`](../Quick_Start.md)。
