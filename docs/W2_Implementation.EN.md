# W2 implementation notes

Details that do not belong in the command-only [`Quick_Start.md`](../Quick_Start.md).

## Chassis (孟子云)

Linkhou `s2_chassis_ws` is owned by the chassis bring-up owner. **Do not edit it** unless they ask.

After their 2026-09 graph change, W2 must run the Zenoh **router first**, and the 3588 must join as a **client** of `192.168.110.69:7447`. Launch with `publish_robot_state:=false`. Full command order: [`../Quick_Start.md`](../Quick_Start.md) **Z1 then C1**.

1. On W2-019: `ros2 run rmw_zenoh_cpp rmw_zenohd` (one process only).
2. `ssh linux@192.168.111.61` (password `linux`) → `distrobox enter ubuntu24`.
3. Stop any previous chassis launch.
4. `echo "$ZENOH_CONFIG_OVERRIDE"` must be  
   `mode="client";connect/endpoints=["tcp/192.168.110.69:7447"]`.  
   If not: `source ~/s2_chassis_ws/.bashrc` **or** `export CHASSIS_ZENOH_REMOTE=1` then `source ~/s2_chassis_ws/config/chassis_env.conf`.
5. `source ~/s2_chassis_ws/install/setup.bash`
6. `ros2 launch linkhou_s2_description chassis_ros2_control.launch.py can_iface:=bcan0 publish_robot_state:=false`

On W2 you should then see `/cmd_vel`, `/chassis/odom`, `/chassis/joint_states`, plus `/chassis/imu`, `/chassis/status`, `/cmd_vel_joy`, `/relative_goal_cmd`, and the other `/chassis/*` names in Quick Start.

Do **not** `unset ZENOH_CONFIG_OVERRIDE` on the 3588 (that would drop the client endpoint). **Do** `unset` it on W2 so the IPC stays the router, not a leftover client of `192.168.111.115`.

Two `rmw_zenohd` instances on 7447 will fail or split the graph. Camera launch should log `Detected running rmw_zenohd` and continue.

### Split graph (camera moves, wheels do not)

**Symptom.** With `RMW_IMPLEMENTATION=rmw_zenoh_cpp` on W2 you see `/camera_head/...` but **no** `/cmd_vel` / `/chassis/*`. `ros2 topic pub /cmd_vel ...` prints forever, yet the base does not move. `ros2 topic pub --once /cmd_vel ...` hangs on `Waiting for at least 1 matching subscription(s)...`.

**Cause (W2-019 AMR).** Camera usually runs with `ROS_DOMAIN_ID=0`. The chassis web **参数配置 → 外域 ROS_DOMAIN_ID** is often `77`: on that domain the chassis (Zenoh client of `6.6.6.100:7447`) exposes `/chassis/v1/*` and `/cmd_vel`. Same Zenoh router, **different domain IDs** → two topic lists. Selecting **自动模式** enables control but does not change domains.

**Fix (required for InternNav live).** Put the chassis ROS nodes on the **same** Zenoh router as W2 (`tcp/192.168.110.69:7447` or wired `tcp/6.6.6.100:7447`), then re-check:

```bash
# On W2 (Zenoh env, router already running)
ros2 topic list | grep -E 'cmd_vel|chassis|camera_head'
ros2 topic info /cmd_vel -v    # must show Subscription count ≥ 1
```

Until `Subscription count ≥ 1` and a short `/cmd_vel` pub moves the base, do **not** run the bridge without `--dry-run`. Ask the chassis owner how the `:8080` stack joins W2’s Zenoh (client endpoint / Distrobox `s2_chassis_ws`). Do not point the camera off Zenoh just to chase chassis topics.

## Camera

Launch: `gemini_330_series_head.launch.py` with `serial_number:=CPC9363000CZ`.  
Not `gemini_336.launch.py`. Not RealSense. Raw RGB is enough if compressed plugins fail.

`rqt_image_view` needs a real display (NoMachine on W2, or `ssh -Y` from zy). Cursor SSH will print `could not connect to display`. Use `scripts/save_head_rgb.py` as a fallback.

## Bridge

- `--rgb-topic /camera_head/color/image_raw`
- `--no-use-sim-time` on hardware
- `--dry-run` until you confirm `/chassis/odom`
- `--no-tuck`; never `--tuck-body` (waist home can tip the base)
- Recommended first live: `--lin-x 0.15 --yaw-rate 0.25 --forward-m 0.25 --turn-deg 12 --step-pause 0.0` (e-stop ready). Use slower flags only if you need more time between motions.
- Log line `Waiting for /head_camera/rgb` is leftover Isaac text
- Exit `Aborted` / `rcl_shutdown already called` is rclpy teardown

`--step-pause` and slower `--lin-x` do **not** make DualVLN “think longer”; they only space or slow execution.

## Safety

E-stop before live `/cmd_vel`. Chassis `cmd_timeout_s` is about **0.5 s**; the bridge pulses Twist during each action. Language-goal quality requires a **moving** camera (live), not a 10-step dry-run.

Validated W2-019 path: domain **77** + web **自动模式** + Zenoh `6.6.6.100:7447`. Compare base vs SocialGen only by changing `--model-path` and restarting the zy server between inits.
