# InternNav DualVLN fine-tune on 1× A6000 (lab)

This is **not** the DualVLN paper recipe (that script is 8×8 GPUs). It is the smallest DualVLN-related job that can run on one **48 GB A6000** so you can participate in W2 fine-tuning without waiting for the 3× A100 box.

**Do this after LightNav-0 is on W2.** Fine-tune does not replace the W2 deployment task.

Official docs: [InternNav training](https://internrobotics.github.io/user_guide/internnav/quick_start/training.html).

## What “W2 / LunarBot fine-tune” actually is

| Goal | Data | GPU | Result |
|------|------|-----|--------|
| Prove the DualVLN train loop | Extracted InternData-N1 **mini** R2R (or IROS PE) | 1× A6000 | A checkpoint that loads; maybe worse than released DualVLN |
| Match DualVLN paper | Full InternData-N1 + System2 then joint | 64 GPUs class | Released DualVLN |
| Specialize to **this lab’s W2** | Teleop / onboard RGB + cmd from W2 | 1–3 GPUs LoRA later | Needs a recorder you do not have yet |
| LunarBot | Same DualVLN weights; Isaac `/rgb` bridge already in `LunarBot-Nav2` | Same | **One model, two robots** — do not train two DualVLNs |

Until W2 demonstrations exist, “fine-tune for W2” = continue DualVLN **System 1** on public VLN trajectories, then **deploy the same ckpt** on W2 (`InternNav-W2` bridge) and LunarBot (`internnav_cmd_vel_bridge.py`).

LightNav-0 **cannot** be fine-tuned with the public repo (inference only).

## Copy to the A6000 PC

You need InternNav + DualVLN weights + **extracted** trajectories. Mini on Sim-06 is mostly `.tar.gz` — extract **a few** R2R scenes, not the whole 486 GB, if the A6000 disk is smaller.

```bash
# On A6000, after InternNav conda exists (same as Sim-06 internnav env)
ln -sfn /path/to/InternVLA-N1-DualVLN ~/InternNav/checkpoints/InternVLA-N1-System2
# Trainer only loads InternVLAN1ForCausalLM if the path string contains internvla-n1-system2.

# Extract 1–2 R2R tars from InternData-N1-mini vln_n1, then:
cd ~/InternNav
ln -sfn /path/to/extracted/vln_n1/traj_data ./traj_data
ls traj_data/r2r   # scene folders with meta/ + data/ + videos/, not only tar.gz
```

Copy this script into InternNav (or run from this repo with a path fix):

```bash
cp ~/InternNav-W2/scripts/train_dual_system_a6000.sh \
  ~/InternNav/scripts/train/qwenvl_train/train_dual_system_a6000.sh
conda activate internnav
cd ~/InternNav
bash scripts/train/qwenvl_train/train_dual_system_a6000.sh
```

Watch `nvidia-smi`. If OOM: set `num_history=2` in the script, or `VLN_DATASETS=r2r_125cm_0_30%5`. If it runs, raise the `%` slowly. Do **not** set `tune_mm_llm True` on one A6000.

The trainer defaults to `flash_attention_2`. If that import fails on the A6000 env, change the last line of `internnav/trainer/internvla_n1_trainer.py` to `train(attn_implementation="sdpa")` for that machine only.

## Even simpler 1-GPU job (CMA, not DualVLN)

If DualVLN System1 still OOMs, InternNav’s **CMA** trainer is written for **one GPU**:

```bash
cd ~/InternNav
# point cma_exp_cfg lerobot_features_dir at IROS PE or mini PE
./scripts/train/base_train/start_train.sh --name cma_train --model cma
```

CMA is **not** what W2 DualVLN serves today. Use it only to debug data + the internnav env on the A6000.

## After a DualVLN A6000 ckpt exists

1. Copy `checkpoints/InternVLA-N1-DualVLN-a6000` to Sim-06.
2. Point DualVLN `start_server.py` at that dir (same `:8087` / `internnav_w2_bridge.py`).
3. Compare against the released DualVLN on the same instruction. Expect a **drop** until data and steps grow.
4. LunarBot: same server, Isaac `internnav_cmd_vel_bridge.py` — no second training run.

## 3× A100 (when the box is free)

Then, and only then, unfreeze more of System 2 or raise batch / dataset fraction. Still not 64 GPUs. Full System2 from Qwen2.5-VL-7B is a cluster job.

## Do not

- Run `sbatch train_dual_system.sh` as shipped on one GPU.
- Fine-tune LightNav-0 (no training code).
- Collect nothing on W2 and expect the model to “learn the lab”.
- Train DualVLN and LightNav vLLM on the same GPU at once.
