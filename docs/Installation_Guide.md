# 安装 — W2 上的 InternNav DualVLN

克隆与权重只放在 **GPU 主机（zy）**（`192.168.110.35`）。W2 工控机需要 ROS 2 Jazzy、`orbbec_camera`（`~/ros2_ws`），以及一份 `internnav_w2_bridge.py`。3588 已有 `s2_chassis_ws`（不要改）。

上游：[InternRobotics/InternNav](https://github.com/InternRobotics/InternNav)

**实验室规定：** DualVLN 使用 **[uv](https://docs.astral.sh/uv/)**，**不要**再用 conda/Miniconda。

## 1. 克隆 InternNav（zy）

国内：GitHub 常需代理或 `gitclone.com` / `ghproxy`（见实验室 FlyingBird 说明）。

```bash
# zy 上常用布局：
#   ~/SocialNav/InternNav
# 或重新克隆：
cd ~
git clone --depth 1 --recursive https://github.com/InternRobotics/InternNav.git ~/InternNav
```

**不要**为了推理把 InternNav 克隆到 W2 或 3588。

## 2. uv 环境（zy）

```bash
# 如未安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env" 2>/dev/null || export PATH="$HOME/.local/bin:$PATH"

cd ~/SocialNav/InternNav   # 或 ~/InternNav
uv venv .venv --python 3.10
source .venv/bin/activate

# RTX 5090 需要较新的 cu128 wheel（sm_120）。避免仅支持 cu124 的旧 Torch。
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

uv pip install -e ".[model]" --no-build-isolation
```

之后激活：

```bash
source ~/SocialNav/InternNav/.venv/bin/activate
```

### flash-attn 说明（RTX 5090 / apt CUDA）

若 `flash-attn` 编译失败：

```bash
export CUDA_HOME=/usr
export PATH="/usr/lib/nvidia-cuda-toolkit/bin:$PATH"
export CC=gcc-12 CXX=g++-12 CUDAHOSTCXX=g++-12
MAX_JOBS=4 FLASH_ATTENTION_FORCE_BUILD=TRUE \
  uv pip install flash-attn==2.7.2.post1 --no-build-isolation --no-cache
```

源码编译常需 **30–60+ 分钟**（本机 `nvcc`，VPN/镜像几乎帮不上忙）。

## 3. DualVLN 权重（仅 zy）

```bash
source ~/SocialNav/InternNav/.venv/bin/activate
export HF_ENDPOINT=https://hf-mirror.com
export HF_HUB_DISABLE_XET=1
mkdir -p ~/SocialNav/InternNav/checkpoints

huggingface-cli download InternRobotics/InternVLA-N1-DualVLN \
  --local-dir ~/SocialNav/InternNav/checkpoints/InternVLA-N1-DualVLN

huggingface-cli download Kaizhen111/InternVLA-N1-DualVLN-SocialGen-10k-3ep-20261115 \
  --local-dir ~/SocialNav/InternNav/checkpoints/InternVLA-N1-DualVLN-SocialGen-10k-3ep-20261115
```

| Checkpoint | 路径（相对 InternNav 工作目录） |
|------------|--------------------------------|
| 基座 DualVLN | `checkpoints/InternVLA-N1-DualVLN` |
| SocialGen 微调 | `checkpoints/InternVLA-N1-DualVLN-SocialGen-10k-3ep-20261115` |

**SocialGen 必需：** 微调目录中须有 `chat_template.json`（若缺失，从基座 DualVLN 目录复制）。否则 `/agent/init` 可能成功，但每次 `step` 报 “No chat template…”。

```bash
BASE=~/SocialNav/InternNav/checkpoints/InternVLA-N1-DualVLN
FT=~/SocialNav/InternNav/checkpoints/InternVLA-N1-DualVLN-SocialGen-10k-3ep-20261115
cp -n "$BASE/chat_template.json" "$FT/chat_template.json"
```

**不要**把权重下到 W2。用 bridge 的 `--model-path` 切换模型（5090 上一次只加载一个 agent；切换时重启 `start_server.py` 以释放显存）。

## 4. 本仓库 → W2 脚本

```bash
scp ~/internnav_w2/scripts/internnav_w2_bridge.py fiveages@192.168.110.69:~/internnav_w2_bridge.py
scp ~/internnav_w2/scripts/save_head_rgb.py fiveages@192.168.110.69:~/save_head_rgb.py
```

W2 为系统 Python **3.12** + ROS `rclpy`，不要在那里安装 InternNav。

## 5. W2 相机包

`~/ros2_ws` 须提供 `orbbec_camera` 与 `gemini_330_series_head.launch.py`。

W2-019 头部序列号：`CPC9363000CZ`（其他 W2 机台可能不同 — 以 Orbbec 机身标签为准）。

若相机因 `diagnostic_updater` 符号错误崩溃，请在 `~/ros2_ws` 中按当前 Jazzy 包重建 `orbbec_camera`。

## 6. 底盘

由底盘负责人维护。W2 上**先**起 `rmw_zenohd`；Distrobox 中 `ZENOH_CONFIG_OVERRIDE` 须指向**本机** W2 的 router。

## 7. 局域网 HTTP

```bash
export NO_PROXY="192.168.110.35,localhost,127.0.0.1"
export no_proxy="$NO_PROXY"
```

下一步：[`../Quick_Start.md`](../Quick_Start.md)。
