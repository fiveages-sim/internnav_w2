# Installation — InternNav DualVLN for W2

Clone and weights go on the **GPU host (zy)** only (`192.168.110.35`). The W2 IPC needs ROS 2 Jazzy, `orbbec_camera` (`~/ros2_ws`), and a copy of `internnav_w2_bridge.py`. The 3588 already has `s2_chassis_ws` (do not modify).

Upstream: [InternRobotics/InternNav](https://github.com/InternRobotics/InternNav)

**Lab policy:** use **[uv](https://docs.astral.sh/uv/)** for DualVLN — **not** conda/Miniconda.

## 1. Clone InternNav (zy)

China: GitHub often needs a proxy or `gitclone.com` / `ghproxy` (see lab FlyingBird notes).

```bash
# Preferred lab layout used on zy:
#   ~/SocialNav/InternNav
# Or a fresh clone:
cd ~
git clone --depth 1 --recursive https://github.com/InternRobotics/InternNav.git ~/InternNav
```

Do **not** clone InternNav onto W2 or the 3588 for inference.

## 2. uv environment (zy)

```bash
# Install uv once if needed
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env" 2>/dev/null || export PATH="$HOME/.local/bin:$PATH"

cd ~/SocialNav/InternNav   # or ~/InternNav
uv venv .venv --python 3.10
source .venv/bin/activate

# RTX 5090 needs a recent cu128 wheel (sm_120). Avoid older cu124-only Torch.
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# InternNav + model deps (flash-attn may need a source build; see notes below)
uv pip install -e ".[model]" --no-build-isolation
```

Activate later:

```bash
source ~/SocialNav/InternNav/.venv/bin/activate
```

### flash-attn notes (RTX 5090 / Ubuntu apt CUDA)

If `flash-attn` fails to build:

```bash
export CUDA_HOME=/usr
export PATH="/usr/lib/nvidia-cuda-toolkit/bin:$PATH"
export CC=gcc-12 CXX=g++-12 CUDAHOSTCXX=g++-12
MAX_JOBS=4 FLASH_ATTENTION_FORCE_BUILD=TRUE \
  uv pip install flash-attn==2.7.2.post1 --no-build-isolation --no-cache
```

Building from source can take **30–60+ minutes** (local `nvcc` compile — VPN/mirrors do not speed this up).

Verify:

```bash
python -c "import torch, flash_attn; print(torch.__version__, torch.cuda.is_available(), flash_attn.__version__)"
```

## 3. DualVLN checkpoints (zy only)

China Hugging Face mirror:

```bash
source ~/SocialNav/InternNav/.venv/bin/activate
export HF_ENDPOINT=https://hf-mirror.com
export HF_HUB_DISABLE_XET=1
mkdir -p ~/SocialNav/InternNav/checkpoints

# Base DualVLN
huggingface-cli download InternRobotics/InternVLA-N1-DualVLN \
  --local-dir ~/SocialNav/InternNav/checkpoints/InternVLA-N1-DualVLN

# Team SocialGen finetune
huggingface-cli download Kaizhen111/InternVLA-N1-DualVLN-SocialGen-10k-3ep-20261115 \
  --local-dir ~/SocialNav/InternNav/checkpoints/InternVLA-N1-DualVLN-SocialGen-10k-3ep-20261115
```

| Checkpoint | Path (under InternNav cwd) |
|------------|----------------------------|
| Base | `checkpoints/InternVLA-N1-DualVLN` |
| SocialGen finetune | `checkpoints/InternVLA-N1-DualVLN-SocialGen-10k-3ep-20261115` |

**Required for SocialGen:** ensure `chat_template.json` exists in the finetune folder (copy from the base DualVLN dir if missing). Without it, `/agent/init` may succeed but every `step` fails with “No chat template is set for this processor.”

```bash
BASE=~/SocialNav/InternNav/checkpoints/InternVLA-N1-DualVLN
FT=~/SocialNav/InternNav/checkpoints/InternVLA-N1-DualVLN-SocialGen-10k-3ep-20261115
cp -n "$BASE/chat_template.json" "$FT/chat_template.json"
```

Do **not** download weights onto W2. Switch models with the bridge `--model-path` (one agent at a time on the 5090 — restart `start_server.py` when switching to free VRAM).

## 4. This repository → W2 scripts

```bash
# Example: W2-019 Wi-Fi
scp ~/internnav_w2/scripts/internnav_w2_bridge.py fiveages@192.168.110.69:~/internnav_w2_bridge.py
scp ~/internnav_w2/scripts/save_head_rgb.py fiveages@192.168.110.69:~/save_head_rgb.py
```

W2 Python is system **3.12** + ROS `rclpy`. Do not install InternNav into that interpreter.

## 5. W2 camera package

`~/ros2_ws` must provide `orbbec_camera` and `gemini_330_series_head.launch.py`.

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
```

W2-019 head serial: `CPC9363000CZ` (other W2 units may differ — check the Orbbec label).

If the camera node dies with `diagnostic_updater` undefined-symbol errors, rebuild `orbbec_camera` in `~/ros2_ws` against current Jazzy packages.

## 6. Chassis

Owned by the chassis bring-up owner (`s2_chassis_ws` / Distrobox). Start `rmw_zenohd` on W2 **first**; Distrobox `ZENOH_CONFIG_OVERRIDE` must point at **this** W2’s router (e.g. `tcp/192.168.110.69:7447` or `tcp/6.6.6.100:7447`).

## 7. LAN HTTP

```bash
export NO_PROXY="192.168.110.35,localhost,127.0.0.1"
export no_proxy="$NO_PROXY"
```

Next: [`../Quick_Start.md`](../Quick_Start.md).
