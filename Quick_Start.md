# Quick Start — InternNav DualVLN on W2

**仅运行时命令。** 不含克隆、uv 虚拟环境或权重下载。首次搭建见 [`docs/Installation_Guide.md`](docs/Installation_Guide.md)。

| ID | 机器 | 提示符 | 角色 |
|----|---------|--------|------|
| **Z1** | W2-019 | `fiveages@W2-019` | Zenoh **router**（`rmw_zenohd`） |
| **C1** | 底盘 | `linux@linux` 再进 Distrobox | Linkhou 启动（Zenoh **client**） |
| **S1** | zy (GPU) | on zy host | DualVLN `:8087` |
| **W1** | W2-019 | `fiveages@W2-019` | 头部相机 |
| **W2** | W2-019 | `fiveages@W2-019` | Bridge / `hz` / `curl` |
| **W3** | W2 桌面（NoMachine） | `fiveages@W2-019` | `rqt_image_view` |

Dry-run 与 live **必须**在 **W2-019** 上运行，不要在 zy。Live 前先急停。`--no-tuck`。**只**跑一个 `rmw_zenohd` — 在底盘接入 **之前**于 W2 启动。不要再起第二个 router（相机 launch 会复用已在跑的那个）。

**Domain ID：** 网页底盘外域默认 **`77`**，相机默认 **`0`** → 两套 `ros2 topic list` 属正常。InternNav 须同一域（推荐相机/rqt/bridge 用 `ROS_DOMAIN_ID=77`；或把网页「外域」改成 `0`）。Zenoh：上肢 router `6.6.6.100:7447`。Live 前网页选**自动模式**。

**建议顺序：** Z1 Zenoh → 网页自动模式 → S1 → W1 相机（domain=外域）→ 同域查话题 → dry-run → `/cmd_vel` 冒烟 → live。

---

## SSH

**W2-019**（从 zy 或任意实验室 PC）：

```bash
ssh fiveages@192.168.110.69
```

用户名 `fiveages`，密码 `123456`。

提示符应变为 `fiveages@W2-019`。打开 **三个** SSH 会话（Zenoh + 相机 + bridge）。

**底盘：**

```bash
ssh linux@192.168.111.61
```

用户名 `linux`，密码 `linux`。提示符 `linux@linux`。

---

## Z1 — Zenoh router（W2-019）

提示符：`fiveages@W2-019`。保持运行。3588 **连到本机**（`192.168.110.69:7447` 或有线 `6.6.6.100:7447`）。

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
unset ZENOH_CONFIG_OVERRIDE
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
export ROS_DOMAIN_ID=0

ros2 run rmw_zenoh_cpp rmw_zenohd
```

期望出现 Zenoh 可在 `tcp/192.168.110.69:7447`（或本机局域网 IP）访问的日志行。**不要**在 W1 或 W2 再起另一个 `rmw_zenohd`。

---

## C1 — 底盘（3588 Distrobox）

在底盘 SSH 会话中。`distrobox enter` 之后**等 Distrobox 就绪**再敲后续命令。不要 `exit` 容器。

```bash
distrobox enter ubuntu24
```

停掉旧的底盘 launch（在该 Distrobox 里 `Ctrl+C`），保证只跑一个 `chassis_ros2_control`。

确认 3588 是 W2 的 Zenoh **client**：

```bash
echo "$ZENOH_CONFIG_OVERRIDE"
```

应类似：

```text
mode="client";connect/endpoints=["tcp/192.168.110.69:7447"]
```

若为空、仍是 `mode="peer"`、或指向别的机器（如 `192.168.111.115`）：

```bash
source ~/s2_chassis_ws/.bashrc
```

或：

```bash
export CHASSIS_ZENOH_REMOTE=1
source ~/s2_chassis_ws/config/chassis_env.conf
```

然后：

```bash
# echo "$ZENOH_CONFIG_OVERRIDE"
# source ~/s2_chassis_ws/install/setup.bash
# export RMW_IMPLEMENTATION=rmw_zenoh_cpp
# export ROS_DOMAIN_ID=0

ros2 launch linkhou_s2_description chassis_ros2_control.launch.py \
  can_iface:=bcan0 publish_robot_state:=false
```

应收到 `mode="client";connect/endpoints=["tcp/192.168.110.69:7447"]`

保持运行。除底盘负责人文档所述外，不要改 `s2_chassis_ws`。

在 W2 上（Z1 + C1 之后），`ros2 topic list` 至少应包含 `/cmd_vel`、`/chassis/odom`、`/chassis/joint_states`。健康的仅底盘图大致如下：

```text
/chassis/auto_mode_enabled
/chassis/battery
/chassis/controller_state
/chassis/drive_policy_fsm
/chassis/dynamic_joint_states
/chassis/imu
/chassis/joint_states
/chassis/motion_pause
/chassis/motor_lifetime
/chassis/move_relative
/chassis/move_relative_done
/chassis/odom
/chassis/robot_description
/chassis/status
/chassis/ultrasonic
/cmd_vel
/cmd_vel_joy
/relative_goal_cmd
/tf
```

（`publish_robot_state:=false` 可避免第二个 robot_state_publisher 与上半身栈冲突。）

**网页底盘**（`http://6.6.6.6:8080/` 或 `http://192.168.110.63:8080/`）：live `/cmd_vel` 前选 **自动模式**。

**Domain ID（W2-019 AMR）。** 网页 **参数配置** 里有两个域：

| 项 | 典型值 | 含义 |
|----|--------|------|
| 平台系统参数 → ROS 工作域 | `0` | 底盘内部 AMR / 雷达 |
| 联机与扩展 → 外域 ROS_DOMAIN_ID | 须与 W2 一致 | 底盘在此外域暴露 `/chassis/v1` 并收 `/cmd_vel` / TF |
| 上肢 Zenoh Router IP | `6.6.6.100` | 底盘 Zenoh **client** → W2 `rmw_zenohd` |
| 上肢 Zenoh 端口 | `7447` | |

若外域是 `77` 而相机/bridge 用 `ROS_DOMAIN_ID=0`，同一 Zenoh router 上会出现**两套话题列表**。统一即可：相机 + bridge + rqt 使用 `export ROS_DOMAIN_ID=77`（与当前网页外域一致），**或**请底盘负责人把外域改成 `0`。

**就绪检查（一个 W2 Zenoh shell，domain = 外域）：**

```bash
ros2 topic list | grep -E 'camera_head/color/image_raw|cmd_vel|chassis'
ros2 topic info /cmd_vel -v
```

必须同时看到**相机 + `/cmd_vel`**，且 `/cmd_vel` 的 **Subscription count ≥ 1**。见 [`docs/W2_Implementation.md`](docs/W2_Implementation.md)「图分裂」。

---

## S1 — zy DualVLN 服务端

提示符：在 **zy** 本机（不要为这一步 SSH 到 W2）。

```bash
source ~/SocialNav/InternNav/.venv/bin/activate
cd ~/SocialNav/InternNav
python scripts/eval/start_server.py --host 0.0.0.0 --port 8087
```

保持运行。期望 `Uvicorn running on http://0.0.0.0:8087`。

---

## W1 — W2 头部相机

提示符：`fiveages@W2-019`。**与 Z1 分开的 SSH。** 保持运行。

Z1 的 router 必须已起来。相机 launch 应打印 `Detected running rmw_zenohd`，并**不要**再起第二个 router。

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
unset ZENOH_CONFIG_OVERRIDE
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
# 须与网页「外域 ROS_DOMAIN_ID」一致（实验室默认 77）
export ROS_DOMAIN_ID=77

ros2 launch orbbec_camera gemini_330_series_head.launch.py serial_number:=CPC9363000CZ
```

期望 Gemini 336L 已连接。可忽略 `compressed_pub` / `theora` 报错。

---

## W2 — W2 检查 + DualVLN bridge

提示符：`fiveages@W2-019`。**再开一个** SSH。与 W1 相同的 `source` / `export`（含 **`ROS_DOMAIN_ID=77`**），再加上：

```bash
export NO_PROXY="192.168.110.35,localhost,127.0.0.1"
export no_proxy="$NO_PROXY"
```

```bash
ros2 topic hz /camera_head/color/image_raw
ros2 topic list | grep -E 'camera_head/color/image_raw|cmd_vel|chassis'
ros2 topic info /cmd_vel -v
curl -sS --connect-timeout 5 http://192.168.110.35:8087/docs | head
ls ~/internnav_w2_bridge.py
```

若缺少 bridge，从 **zy**：

```bash
scp ~/internnav_w2/scripts/internnav_w2_bridge.py fiveages@192.168.110.69:~/internnav_w2_bridge.py
```

### 运行基座 DualVLN 与 SocialGen 微调

| 模型 | `--model-path`（相对 zy 上 InternNav 工作目录） |
|------|------------------------------------------------|
| **原版** DualVLN | `checkpoints/InternVLA-N1-DualVLN` |
| **微调** SocialGen | `checkpoints/InternVLA-N1-DualVLN-SocialGen-10k-3ep-20261115` |

两者共通：

- 5090 上一次约只能加载一个 agent。切换模型，或 dry-run 后再 live 若 `/agent/init` 返回 **500**，须在 zy 上**重启** `start_server.py`。
- SocialGen 目录须含 `chat_template.json`（缺失则从基座复制）。
- Bridge shell：`ROS_DOMAIN_ID=77`、Zenoh、`NO_PROXY` 含 `192.168.110.35`。
- 轮子能动 + `InternNav init OK` 说明**链路正确**。没找到语言目标（如椅子）多为**模型 / 场景 / 指令**问题，不是接线错误——DualVLN 是离散 VLN（看/转/进），不保证目标搜索；`-1` WAIT 在 W2 上**不会**低头；过早 `Ctrl+C`（约 20 步）常在搜完前结束。

**Dry-run**（不转轮）— 二选一 `--model-path`：

```bash
# 原版 DualVLN
python3 ~/internnav_w2_bridge.py \
  --host 192.168.110.35 --port 8087 \
  --model-path checkpoints/InternVLA-N1-DualVLN \
  --rgb-topic /camera_head/color/image_raw \
  --no-use-sim-time --width 640 --height 480 \
  --instruction "Find the black chair" \
  --dry-run --no-tuck --max-steps 10

# 微调 SocialGen（若刚跑过基座，先重启服务端）
python3 ~/internnav_w2_bridge.py \
  --host 192.168.110.35 --port 8087 \
  --model-path checkpoints/InternVLA-N1-DualVLN-SocialGen-10k-3ep-20261115 \
  --rgb-topic /camera_head/color/image_raw \
  --no-use-sim-time --width 640 --height 480 \
  --instruction "Find the black chair" \
  --dry-run --no-tuck --max-steps 10
```

期望 `InternNav init OK` 与 `step N/10 … action=…`。退出时的 core dump 多为 rclpy 拆除噪声。

**Live** — 网页**自动模式**、急停就绪、`/cmd_vel` 冒烟已通过。dry-run 后先重启服务端。去掉 `--dry-run`：

```bash
# 原版 DualVLN
python3 ~/internnav_w2_bridge.py \
  --host 192.168.110.35 --port 8087 \
  --model-path checkpoints/InternVLA-N1-DualVLN \
  --rgb-topic /camera_head/color/image_raw \
  --no-use-sim-time --width 640 --height 480 \
  --instruction "Find the black chair" \
  --no-tuck \
  --lin-x 0.15 --yaw-rate 0.25 --forward-m 0.25 --turn-deg 12 \
  --step-pause 0.0 --max-steps 100

# 微调 SocialGen
python3 ~/internnav_w2_bridge.py \
  --host 192.168.110.35 --port 8087 \
  --model-path checkpoints/InternVLA-N1-DualVLN-SocialGen-10k-3ep-20261115 \
  --rgb-topic /camera_head/color/image_raw \
  --no-use-sim-time --width 640 --height 480 \
  --instruction "Find the black chair" \
  --no-tuck \
  --lin-x 0.15 --yaw-rate 0.25 --forward-m 0.25 --turn-deg 12 \
  --step-pause 0.0 --max-steps 100
```

腾出空间，观察首次 FORWARD/TURN。`Ctrl+C` 后：

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{}"
```

---

## W3 — rqt（头部 RGB）

头部相机是 **Orbbec**，不是 RealSense。话题：`/camera_head/color/image_raw`。

**不要**在 Cursor SSH 标签页里跑（`could not connect to display`）。在 W2-019 上用 **NoMachine**，在**远程桌面**的终端里：

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
unset ZENOH_CONFIG_OVERRIDE
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
export ROS_DOMAIN_ID=77
ros2 run rqt_image_view rqt_image_view
```

下拉选择：`/camera_head/color/image_raw`。

或从 zy 本机桌面：`ssh -Y fiveages@192.168.110.69` 再执行同样命令。必须已设置 `$DISPLAY`。

无 GUI 保存一帧（W2 SSH 即可）：

```bash
python3 ~/save_head_rgb.py --out /tmp/w2_head_rgb.png
```

（如需，先把 `scripts/save_head_rgb.py` `scp` 到 W2。）

---

## 停止

1. W2 上的 bridge（`Ctrl+C`）
2. rqt
3. W1 上的相机 launch
4. S1 上的 DualVLN
5. C1 上的底盘 launch（`Ctrl+C`）
6. Z1 上的 Zenoh router（`Ctrl+C`）
