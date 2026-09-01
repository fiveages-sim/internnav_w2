# Quick Start — InternNav DualVLN on W2

**Runtime commands only.** No clone, conda, or weight download. For first-time setup see [`docs/Installation_Guide.md`](docs/Installation_Guide.md).

| ID | Machine | Prompt | Role |
|----|---------|--------|------|
| **C1** | Chassis | `linux@linux` then Distrobox | Linkhou launch |
| **S1** | Sim-06 | `fiveages@Sim-06` | DualVLN `:8087` |
| **W1** | W2-0035 | `fiveages@W2-0035` | Head camera |
| **W2** | W2-0035 | `fiveages@W2-0035` | Bridge / `hz` / `curl` |
| **W3** | W2 desktop (NoMachine) | `fiveages@W2-0035` | `rqt_image_view` |

Dry-run and live **must** run on **W2-0035**, not Sim-06. E-stop before live. `--no-tuck`. Do not start a second `rmw_zenohd` if one is already up.

**Suggested order:** C1 chassis → S1 server → SSH to W2 → W1 camera → W2 check topics → dry-run → live.

---

## SSH

**W2-0035** (from Sim-06 or any lab PC):

```bash
ssh fiveages@192.168.111.223
```

Username `fiveages`, password `123456`.


Prompt must become `fiveages@W2-0035`. Open **two** SSH sessions (camera + bridge).

**Chassis:**

```bash
ssh linux@192.168.111.35
```

Username `linux`, password `linux`. Prompt `linux@linux`.

---

## C1 — Chassis (3588)

On the chassis SSH session:

```bash
distrobox enter ubuntu24
source ~/s2_chassis_ws/install/setup.bash
ros2 launch linkhou_s2_description chassis_ros2_control.launch.py can_iface:=bcan0
```

Leave this running. Do not edit `s2_chassis_ws`.

On W2 you should later see `/cmd_vel`, `/chassis/odom`, `/chassis/joint_states` (same graph as the camera).

---

## S1 — Sim-06 DualVLN server

Prompt: `fiveages@Sim-06` (do **not** SSH).

```bash
conda activate internnav
cd ~/InternNav
python scripts/eval/start_server.py --host 0.0.0.0 --port 8087
```

Leave running. Expect `Uvicorn running on http://0.0.0.0:8087`.

---

## W1 — W2 head camera

Prompt: `fiveages@W2-0035`. Leave running.

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
unset ZENOH_CONFIG_OVERRIDE
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
export ROS_DOMAIN_ID=0

ros2 launch orbbec_camera gemini_330_series_head.launch.py serial_number:=CPC6463000WX
```

Expect Gemini 336L connected. Ignore `compressed_pub` / `theora` errors.

---

## W2 — W2 check + DualVLN bridge

Prompt: `fiveages@W2-0035`. **Second** SSH. Same `source` / `export` as W1, plus:

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

If the bridge is missing, from **Sim-06**:

```bash
scp ~/InternNav-W2/scripts/internnav_w2_bridge.py fiveages@192.168.111.223:~/internnav_w2_bridge.py
```

**Dry-run** (no wheels) — still on W2-0035:

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

**Live** (e-stop; `/chassis/odom` must be live):

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

## W3 — rqt (head RGB)

Head camera is **Orbbec**, not RealSense. Topic: `/camera_head/color/image_raw`.

Do **not** run this in a Cursor SSH tab (`could not connect to display`). Use **NoMachine** on W2-0035, terminal **on the remote desktop**:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
unset ZENOH_CONFIG_OVERRIDE
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
export ROS_DOMAIN_ID=0
ros2 run rqt_image_view rqt_image_view
```

Dropdown: `/camera_head/color/image_raw`.

Or from Sim-06’s own desktop: `ssh -Y fiveages@192.168.111.223` then the same. `$DISPLAY` must be set.

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
