# W2 implementation notes

Details that do not belong in the command-only [`Quick_Start.md`](../Quick_Start.md).

## Chassis (孟子云)

To have `/chassis/*` and `/cmd_vel` on W2-0035:

1. `ssh linux@192.168.111.35` (password `linux`)
2. `distrobox enter ubuntu24`
3. `source ~/s2_chassis_ws/install/setup.bash`
4. `ros2 launch linkhou_s2_description chassis_ros2_control.launch.py can_iface:=bcan0`

Do **not** edit `s2_chassis_ws`. If W2 still has no chassis topics, the 3588 Zenoh **client** must `connect` to the **router** (often W2-0035 `192.168.111.223:7447`). Leftover `ZENOH_CONFIG_OVERRIDE` pointing at another PC (e.g. `192.168.111.115`) breaks discovery — `unset` it on W2.

Default launch may start its own `rmw_zenohd` on W2 when the camera comes up first. One router only.

## Camera

Launch: `gemini_330_series_head.launch.py` with `serial_number:=CPC6463000WX`.  
Not `gemini_336.launch.py`. Not RealSense. Raw RGB is enough if compressed plugins fail.

`rqt_image_view` needs a real display (NoMachine on W2, or `ssh -Y` from Sim-06). Cursor SSH will print `could not connect to display`. Use `scripts/save_head_rgb.py` as a fallback.

## Bridge

- `--rgb-topic /camera_head/color/image_raw`
- `--no-use-sim-time` on hardware
- `--dry-run` until you confirm `/chassis/odom`
- `--no-tuck`; never `--tuck-body` (waist home can tip the base)
- Slow live defaults used in lab: `--lin-x 0.08 --yaw-rate 0.12 --forward-m 0.10 --turn-deg 6 --step-pause 1.0`
- Log line `Waiting for /head_camera/rgb` is leftover Isaac text
- Exit `Aborted` / `rcl_shutdown already called` is rclpy teardown

`--step-pause` and slower `--lin-x` do **not** make DualVLN “think longer”; they only space or slow execution.

## Safety

E-stop before live `/cmd_vel`. Chassis `cmd_timeout_s` is about **0.5 s**; the bridge pulses Twist during each action. Language-goal quality requires a **moving** camera (live), not a 10-step dry-run.
