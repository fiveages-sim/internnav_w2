# W2 实现说明

不宜放进仅命令的 [`Quick_Start.md`](../Quick_Start.md) 的细节。

## 底盘（孟子云）

Linkhou `s2_chassis_ws` 由底盘联调负责人维护。**除非对方要求，否则不要修改。**

其 2026-09 图变更之后，W2 必须**先**跑 Zenoh **router**，3588 须作为 `192.168.110.69:7447` 的 **client** 加入。Launch 使用 `publish_robot_state:=false`。完整命令顺序：[`../Quick_Start.md`](../Quick_Start.md) **先 Z1 再 C1**。

1. 在 W2-019：`ros2 run rmw_zenoh_cpp rmw_zenohd`（仅一个进程）。
2. `ssh linux@192.168.111.61`（密码 `linux`）→ `distrobox enter ubuntu24`。
3. 停掉此前的底盘 launch。
4. `echo "$ZENOH_CONFIG_OVERRIDE"` 必须为  
   `mode="client";connect/endpoints=["tcp/192.168.110.69:7447"]`。  
   若不是：`source ~/s2_chassis_ws/.bashrc` **或** `export CHASSIS_ZENOH_REMOTE=1` 再 `source ~/s2_chassis_ws/config/chassis_env.conf`。
5. `source ~/s2_chassis_ws/install/setup.bash`
6. `ros2 launch linkhou_s2_description chassis_ros2_control.launch.py can_iface:=bcan0 publish_robot_state:=false`

此后在 W2 上应能看到 `/cmd_vel`、`/chassis/odom`、`/chassis/joint_states`，以及 `/chassis/imu`、`/chassis/status`、`/cmd_vel_joy`、`/relative_goal_cmd` 和 Quick Start 中的其他 `/chassis/*` 名称。

**不要**在 3588 上 `unset ZENOH_CONFIG_OVERRIDE`（会丢掉 client 端点）。在 W2 上**要** `unset`，让工控机保持为 router，而不是残留成 `192.168.111.115` 的 client。

7447 上两个 `rmw_zenohd` 会失败或分裂图。相机 launch 应打出 `Detected running rmw_zenohd` 并继续。

### 图分裂（相机正常，轮子不动）

**现象。** W2 上 `RMW_IMPLEMENTATION=rmw_zenoh_cpp` 时能看到 `/camera_head/...`，但**没有** `/cmd_vel` / `/chassis/*`。`ros2 topic pub /cmd_vel ...` 一直在刷，车却不动；`--once` 卡在 `Waiting for at least 1 matching subscription(s)...`。

**原因（W2-019 AMR）。** 相机通常用 `ROS_DOMAIN_ID=0`。网页 **参数配置 → 外域 ROS_DOMAIN_ID** 常为 `77`：底盘以 Zenoh client 连 `6.6.6.100:7447`，在该域暴露 `/chassis/v1/*` 与 `/cmd_vel`。同一 Zenoh router、**不同 domain** → 两套话题。选 **自动模式** 只开控制，不改 domain。


**修复（InternNav live 必需）。** 让底盘 ROS 节点加入与 W2 相同的 Zenoh router（`tcp/192.168.110.69:7447` 或有线 `tcp/6.6.6.100:7447`），再检查：

```bash
ros2 topic list | grep -E 'cmd_vel|chassis|camera_head'
ros2 topic info /cmd_vel -v    # Subscription count 必须 ≥ 1
```

在订阅者 ≥ 1 且短时 `/cmd_vel` 能让车动之前，bridge **不要**去掉 `--dry-run`。向底盘负责人确认 `:8080` 栈如何以 client 接入 W2 Zenoh（或 Distrobox `s2_chassis_ws`）。不要为了追底盘话题而把相机挪出 Zenoh。

## 相机

Launch：`gemini_330_series_head.launch.py`，带 `serial_number:=CPC9363000CZ`。  
不是 `gemini_336.launch.py`。不是 RealSense。若压缩插件失败，原始 RGB 即可。

`rqt_image_view` 需要真实显示器（W2 上 NoMachine，或从 zy `ssh -Y`）。Cursor SSH 会打印 `could not connect to display`。备用：`scripts/save_head_rgb.py`。

## Bridge

- `--rgb-topic /camera_head/color/image_raw`
- 真机上用 `--no-use-sim-time`
- 确认 `/chassis/odom` 之前用 `--dry-run`
- `--no-tuck`；切勿 `--tuck-body`（腰部回零可能让底盘倾倒）
- 首次 live 建议：`--lin-x 0.15 --yaw-rate 0.25 --forward-m 0.25 --turn-deg 12 --step-pause 0.0`（急停就绪）。仅在需要更长间隔时再放慢。
- 日志行 `Waiting for /head_camera/rgb` 是遗留的 Isaac 文案
- 退出时的 `Aborted` / `rcl_shutdown already called` 属于 rclpy 拆除

`--step-pause` 与更慢的 `--lin-x` **不会**让 DualVLN「想更久」；只拉长间隔或放慢执行。

## 安全

Live `/cmd_vel` 前先急停。底盘 `cmd_timeout_s` 约 **0.5 s**；bridge 在每个动作期间脉冲 Twist。语言目标质量需要**运动中的**相机（live），不是 10 步 dry-run。

已验证 W2-019 路径：外域 **77** + 网页**自动模式** + Zenoh `6.6.6.100:7447`。对比基座与 SocialGen 时只改 `--model-path`，并在两次 init 之间重启 zy 服务端。
