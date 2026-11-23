#!/usr/bin/env bash
# DualVLN System-1 continuation on a single A6000 (48 GB).
# Freeze Qwen2.5-VL; train NextDiT / System1 heads only.
# Official train_dual_system.sh is 8 nodes × 8 GPUs — do not run that here.
#
# Prereqs (on the A6000 PC):
#   source ~/SocialNav/InternNav/.venv/bin/activate
#   cd ~/InternNav
#   DualVLN (or System2) weights under checkpoints/InternVLA-N1-System2
#     If you only have InternVLA-N1-DualVLN:
#       ln -sfn InternVLA-N1-DualVLN checkpoints/InternVLA-N1-System2
#   Extracted InternData trajectories at ./traj_data/r2r  (LeRobot dirs, not .tar.gz)
#     ln -sfn ~/InternData-N1-mini/vln_n1/traj_data ./traj_data
#
# This is a smoke / lab-scale run, not the DualVLN paper recipe.

set -euo pipefail
if [[ -f internnav/trainer/internvla_n1_trainer.py ]]; then
  :
elif [[ -f "${HOME}/InternNav/internnav/trainer/internvla_n1_trainer.py" ]]; then
  cd "${HOME}/InternNav"
else
  echo "Run from InternNav root (need internnav/trainer/internvla_n1_trainer.py)." >&2
  exit 1
fi

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export HF_HUB_DISABLE_XET=1

deepspeed=scripts/train/qwenvl_train/zero2.json
system2_ckpt="${SYSTEM2_CKPT:-checkpoints/InternVLA-N1-System2}"
output_dir="${OUTPUT_DIR:-checkpoints/InternVLA-N1-DualVLN-a6000}"
run_name=InternVLA-N1-DualVLN-a6000
# Tiny slice: one height/pitch, 10% of episodes. Raise % after it fits.
vln_datasets="${VLN_DATASETS:-r2r_125cm_0_30%10}"

if [[ ! -d "$system2_ckpt" ]]; then
  echo "Missing $system2_ckpt" >&2
  echo "ln -sfn InternVLA-N1-DualVLN checkpoints/InternVLA-N1-System2" >&2
  exit 1
fi
if [[ ! -d traj_data/r2r ]]; then
  echo "Missing ./traj_data/r2r from InternNav cwd. Extract mini tars, then:" >&2
  echo "  ln -sfn /path/to/InternData-N1-mini/vln_n1/traj_data ./traj_data" >&2
  exit 1
fi

mkdir -p "$output_dir"

torchrun --standalone --nproc_per_node=1 \
  internnav/trainer/internvla_n1_trainer.py \
  --deepspeed "${deepspeed}" \
  --model_name_or_path "${system2_ckpt}" \
  --vln_dataset_use "${vln_datasets}" \
  --data_flatten False \
  --tune_mm_vision False \
  --tune_mm_mlp False \
  --tune_mm_llm False \
  --bf16 \
  --num_history 4 \
  --data_augmentation False \
  --resize_h 384 \
  --resize_w 384 \
  --sample_step 4 \
  --num_future_steps 4 \
  --predict_step_num 32 \
  --pixel_goal_only True \
  --system1 nextdit_async \
  --output_dir "${output_dir}" \
  --num_train_epochs 1.0 \
  --per_device_train_batch_size 1 \
  --per_device_eval_batch_size 1 \
  --gradient_accumulation_steps 4 \
  --max_pixels 313600 \
  --min_pixels 3136 \
  --eval_strategy no \
  --save_strategy steps \
  --save_steps 200 \
  --save_total_limit 2 \
  --learning_rate 1e-4 \
  --weight_decay 0 \
  --warmup_ratio 0.003 \
  --max_grad_norm 1 \
  --lr_scheduler_type cosine \
  --logging_steps 1 \
  --model_max_length 4096 \
  --gradient_checkpointing True \
  --dataloader_num_workers 2 \
  --run_name "${run_name}" \
  --report_to none
