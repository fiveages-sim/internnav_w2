# Quick Start — InternNav DualVLN on W2

**Runtime commands only.** No clone, uv venv, or weight download. For first-time setup see [`docs/Installation_Guide.md`](docs/Installation_Guide.md).

| ID | Machine | Prompt | Role |
|----|---------|--------|------|
| **Z1** | W2-019 | `fiveages@W2-019` | Zenoh **router** (`rmw_zenohd`) |
| **C1** | Chassis | `linux@linux` then Distrobox | Linkhou launch (Zenoh **client**) |
| **S1** | zy (GPU) | on zy host | DualVLN `:8087` |
| **W1** | W2-019 | `fiveages@W2-019` | Head camera |
| **W2** | W2-019 | `fiveages@W2-019` | Bridge / `hz` / `curl` |
| **W3** | W2 desktop (NoMachine) | `fiveages@W2-019` | `rqt_image_view` |

Dry-run and live **must** run on **W2-019**, not zy. E-stop before live. `--no-tuck`. **One** `rmw_zenohd` only — start it on W2 **before** the chassis launch. Do not start a second router (camera launch will reuse the running one).

**Suggested order:** Z1 Zenoh router → C1 chassis → S1 server → W1 camera → W2 check topics → dry-run → live.

---

## SSH

**W2-019** (from zy or any lab PC):

```bash
ssh fiveages@192.168.110.69
```

Username `fiveages`, password `123456`.

Prompt must become `fiveages@W2-019`. Open **three** SSH sessions (Zenoh + camera + bridge).

**Chassis:**

```bash
ssh linux@192.168.111.61
```

Username `linux`, password `linux`. Prompt `linux@linux`.

---

## Z1 — Zenoh router (W2-019)

Prompt: `fiveages@W2-019`. Leave running. The 3588 connects **to this host** (`192.168.110.69:7447` or wired `6.6.6.100:7447`).

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
unset ZENOH_CONFIG_OVERRIDE
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
export ROS_DOMAIN_ID=0

ros2 run rmw_zenoh_cpp rmw_zenohd
```

Expect a line that Zenoh can be reached at `tcp/192.168.110.69:7447` (or this host’s LAN IP). Do **not** start another `rmw_zenohd` in W1 or W2.

---

## C1 — Chassis (3588 Distrobox)

On the chassis SSH session. **Wait for Distrobox** after `distrobox enter` before the next lines. Do not `exit` the container.

```bash
distrobox enter ubuntu24
```

Stop any old chassis launch (`Ctrl+C` in that Distrobox) so only one `chassis_ros2_control` is running.

Confirm the 3588 is a Zenoh **client** of W2:

```bash
echo "$ZENOH_CONFIG_OVERRIDE"
```

It should look like:

```text
mode="client";connect/endpoints=["tcp/192.168.110.69:7447"]
```

If it is empty, still has `mode="peer"`, or points at another PC (e.g. `192.168.111.115`):

```bash
source ~/s2_chassis_ws/.bashrc
```

or:

```bash
export CHASSIS_ZENOH_REMOTE=1
source ~/s2_chassis_ws/config/chassis_env.conf
```

Then:

```bash
# echo "$ZENOH_CONFIG_OVERRIDE"
# source ~/s2_chassis_ws/install/setup.bash
# export RMW_IMPLEMENTATION=rmw_zenoh_cpp
# export ROS_DOMAIN_ID=0

ros2 launch linkhou_s2_description chassis_ros2_control.launch.py \
  can_iface:=bcan0 publish_robot_state:=false
```

You should receive `mode="client";connect/endpoints=["tcp/192.168.110.69:7447"]`

Leave this running. Do not edit `s2_chassis_ws` except as the chassis owner documents.

On W2 (after Z1 + C1), `ros2 topic list` should include at least `/cmd_vel`, `/chassis/odom`, `/chassis/joint_states`. A healthy chassis-only graph looks like:

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

(`publish_robot_state:=false` avoids a second robot_state_publisher fighting the upper-body stack.)

---

## S1 — zy DualVLN server

Prompt: on **zy** (do **not** SSH to W2 for this).

```bash
source ~/SocialNav/InternNav/.venv/bin/activate
cd ~/SocialNav/InternNav
python scripts/eval/start_server.py --host 0.0.0.0 --port 8087
```

Leave running. Expect `Uvicorn running on http://0.0.0.0:8087`.

---

## W1 — W2 head camera

Prompt: `fiveages@W2-019`. **Separate SSH from Z1.** Leave running.

Z1’s router must already be up. Camera launch should print `Detected running rmw_zenohd` and **not** start a second router.

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
unset ZENOH_CONFIG_OVERRIDE
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
export ROS_DOMAIN_ID=0

ros2 launch orbbec_camera gemini_330_series_head.launch.py serial_number:=CPC9363000CZ
```

Expect Gemini 336L connected. Ignore `compressed_pub` / `theora` errors.

---

## W2 — W2 check + DualVLN bridge

Prompt: `fiveages@W2-019`. **Another** SSH. Same `source` / `export` as W1, plus:

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

If the bridge is missing, from **zy**:

```bash
scp ~/internnav_w2/scripts/internnav_w2_bridge.py fiveages@192.168.110.69:~/internnav_w2_bridge.py
```

**Checkpoints** (on zy under InternNav; pass via `--model-path`):

| Model | `--model-path` |
|-------|----------------|
| Base DualVLN | `checkpoints/InternVLA-N1-DualVLN` |
| SocialGen finetune | `checkpoints/InternVLA-N1-DualVLN-SocialGen-10k-3ep-20261115` |

Restart `start_server.py` on zy when switching models (one agent ≈ fills a 5090). SocialGen needs `chat_template.json` in its checkpoint dir (copy from base if missing).

**Dry-run** (no wheels) — still on W2:

```bash
# Base DualVLN
python3 ~/internnav_w2_bridge.py \
  --host 192.168.110.35 \
  --port 8087 \
  --model-path checkpoints/InternVLA-N1-DualVLN \
  --rgb-topic /camera_head/color/image_raw \
  --no-use-sim-time \
  --width 640 --height 480 \
  --instruction "Find the black chair" \
  --dry-run \
  --no-tuck \
  --max-steps 10

# SocialGen finetune — same flags, change --model-path only
# --model-path checkpoints/InternVLA-N1-DualVLN-SocialGen-10k-3ep-20261115
```

Expect `InternNav init OK` then `step N/10 … action=…`. A core dump on exit is often rclpy teardown noise after steps finish.

**Live** — only after Z1 + C1 + healthy `/chassis/odom` (e-stop in hand). Drop `--dry-run`. Prefer SocialGen if that is the model under test:

```bash
python3 ~/internnav_w2_bridge.py \
  --host 192.168.110.35 \
  --port 8087 \
  --model-path checkpoints/InternVLA-N1-DualVLN-SocialGen-10k-3ep-20261115 \
  --rgb-topic /camera_head/color/image_raw \
  --no-use-sim-time \
  --width 640 --height 480 \
  --instruction "Find the black chair" \
  --no-tuck \
  --lin-x 0.15 \
  --yaw-rate 0.25 \
  --forward-m 0.25 \
  --turn-deg 12 \
  --step-pause 0.0 \
  --max-steps 50
```

Clear space, watch wheels on the first FORWARD/TURN. Stop with `Ctrl+C`, then:

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{}"
```

---

## W3 — rqt (head RGB)

Head camera is **Orbbec**, not RealSense. Topic: `/camera_head/color/image_raw`.

Do **not** run this in a Cursor SSH tab (`could not connect to display`). Use **NoMachine** on W2-019, terminal **on the remote desktop**:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
unset ZENOH_CONFIG_OVERRIDE
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
export ROS_DOMAIN_ID=0
ros2 run rqt_image_view rqt_image_view
```

Dropdown: `/camera_head/color/image_raw`.

Or from zy’s own desktop: `ssh -Y fiveages@192.168.110.69` then the same. `$DISPLAY` must be set.

Save one frame without GUI (W2 SSH OK):

```bash
python3 ~/save_head_rgb.py --out /tmp/w2_head_rgb.png
```

(`scp` `scripts/save_head_rgb.py` to W2 first if needed.)

---

## Stop

1. Bridge on W2 (`Ctrl+C`)
2. rqt
3. Camera launch on W1
4. DualVLN on S1
5. Chassis launch on C1 (`Ctrl+C`)
6. Zenoh router on Z1 (`Ctrl+C`)
