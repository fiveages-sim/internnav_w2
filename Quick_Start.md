# Quick Start — InternNav DualVLN on W2

**仅运行时命令。** 不含克隆、conda 或权重下载。首次搭建见 [`docs/Installation_Guide.md`](docs/Installation_Guide.md)。

| ID | 机器 | 提示符 | 角色 |
|----|---------|--------|------|
| **Z1** | W2-0035 | `fiveages@W2-0035` | Zenoh **router**（`rmw_zenohd`） |
| **C1** | 底盘 | `linux@linux` 再进 Distrobox | Linkhou 启动（Zenoh **client**） |
| **S1** | Sim-06 | `fiveages@Sim-06` | DualVLN `:8087` |
| **W1** | W2-0035 | `fiveages@W2-0035` | 头部相机 |
| **W2** | W2-0035 | `fiveages@W2-0035` | Bridge / `hz` / `curl` |
| **W3** | W2 桌面（NoMachine） | `fiveages@W2-0035` | `rqt_image_view` |

Dry-run 与 live **必须**在 **W2-0035** 上运行，不要在 Sim-06。Live 前先急停。`--no-tuck`。**只**跑一个 `rmw_zenohd` — 在底盘 launch **之前**于 W2 启动。不要再起第二个 router（相机 launch 会复用已在跑的那个）。

**建议顺序：** Z1 Zenoh router → C1 底盘 → S1 服务端 → W1 相机 → W2 检查话题 → dry-run → live。

---

## SSH

**W2-0035**（从 Sim-06 或任意实验室 PC）：

```bash
ssh fiveages@192.168.111.223
```

用户名 `fiveages`，密码 `123456`。

提示符应变为 `fiveages@W2-0035`。打开 **三个** SSH 会话（Zenoh + 相机 + bridge）。

**底盘：**

```bash
ssh linux@192.168.111.61
```

用户名 `linux`，密码 `linux`。提示符 `linux@linux`。

---

## Z1 — Zenoh router（W2-0035）

提示符：`fiveages@W2-0035`。保持运行。3588 **连到本机**（`192.168.111.223:7447`）。

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
unset ZENOH_CONFIG_OVERRIDE
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
export ROS_DOMAIN_ID=0

ros2 run rmw_zenoh_cpp rmw_zenohd
```

期望出现 Zenoh 可在 `tcp/192.168.111.223:7447` 访问的日志行。**不要**在 W1 或 W2 再起另一个 `rmw_zenohd`。

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
mode="client";connect/endpoints=["tcp/192.168.111.223:7447"]
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

应收到 `mode="client";connect/endpoints=["tcp/192.168.111.223:7447"]`

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

---

## S1 — Sim-06 DualVLN 服务端

提示符：`fiveages@Sim-06`（**不要**再 SSH）。

```bash
conda activate internnav
cd ~/InternNav
python scripts/eval/start_server.py --host 0.0.0.0 --port 8087
```

保持运行。期望 `Uvicorn running on http://0.0.0.0:8087`。

---

## W1 — W2 头部相机

提示符：`fiveages@W2-0035`。**与 Z1 分开的 SSH。** 保持运行。

Z1 的 router 必须已起来。相机 launch 应打印 `Detected running rmw_zenohd`，并**不要**再起第二个 router。

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
unset ZENOH_CONFIG_OVERRIDE
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
export ROS_DOMAIN_ID=0

ros2 launch orbbec_camera gemini_330_series_head.launch.py serial_number:=CPC6463000WX
```

期望 Gemini 336L 已连接。可忽略 `compressed_pub` / `theora` 报错。

---

## W2 — W2 检查 + DualVLN bridge

提示符：`fiveages@W2-0035`。**再开一个** SSH。与 W1 相同的 `source` / `export`，再加上：

```bash
export NO_PROXY="192.168.110.35,localhost,127.0.0.1"
export no_proxy="$NO_PROXY"
```

```bash
ros2 topic hz /camera_head/color/image_raw
ros2 topic hz /chassis/odom
ros2 topic list | grep -E 'camera_head/color/image_raw|cmd_vel|chassis/odom'
curl -sS --connect-timeout 5 http://192.168.110.35:8087/docs | head
ls ~/internnav_w2_bridge.py
```

若缺少 bridge，从 **Sim-06**：

```bash
scp ~/InternNav-W2/scripts/internnav_w2_bridge.py fiveages@192.168.111.223:~/internnav_w2_bridge.py
```

**Dry-run**（不转轮）— 仍在 W2-0035：

```bash
python3 ~/internnav_w2_bridge.py \
  --host 192.168.110.35 \
  --port 8087 \
  --rgb-topic /camera_head/color/image_raw \
  --no-use-sim-time \
  --width 640 --height 480 \
  --instruction "Find the black chair" \
  --dry-run \
  --no-tuck \
  --max-steps 10
```

**Live**（急停就绪；`/chassis/odom` 必须在更新）：

```bash
python3 ~/internnav_w2_bridge.py \
  --host 192.168.110.35 \
  --port 8087 \
  --rgb-topic /camera_head/color/image_raw \
  --no-use-sim-time \
  --width 640 --height 480 \
  --instruction "Find the black chair" \
  --no-tuck \
  --lin-x 0.08 \
  --yaw-rate 0.12 \
  --forward-m 0.10 \
  --turn-deg 6 \
  --step-pause 1.0 \
  --max-steps 50
```

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{}"
```

---

## W3 — rqt（头部 RGB）

头部相机是 **Orbbec**，不是 RealSense。话题：`/camera_head/color/image_raw`。

**不要**在 Cursor SSH 标签页里跑（`could not connect to display`）。在 W2-0035 上用 **NoMachine**，在**远程桌面**的终端里：

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
unset ZENOH_CONFIG_OVERRIDE
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
export ROS_DOMAIN_ID=0
ros2 run rqt_image_view rqt_image_view
```

下拉选择：`/camera_head/color/image_raw`。

或从 Sim-06 本机桌面：`ssh -Y fiveages@192.168.111.223` 再执行同样命令。必须已设置 `$DISPLAY`。

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
