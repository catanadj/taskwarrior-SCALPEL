#!/usr/bin/env bash
set -euo pipefail

echo "AI Plan Tasks (interactive)"
echo "Select mode:"
echo "  1) project"
echo "  2) filter"
echo "  3) goal"
echo "  4) new-project"
read -r mode

read -r -p "Prompt: " prompt
read -r -p "Output path [build/task_import.json]: " out_path
out_path=${out_path:-build/task_import.json}

read -r -p "Out mode (selected|delta|full) [selected]: " out_mode
out_mode=${out_mode:-selected}

read -r -p "LM Studio base URL [http://127.0.0.1:1234]: " base_url
base_url=${base_url:-http://127.0.0.1:1234}

read -r -p "Model [ministral-3-14b-reasoning]: " model
model=${model:-ministral-3-14b-reasoning}

read -r -p "Max prompt chars [9000]: " max_prompt
max_prompt=${max_prompt:-9000}

read -r -p "Max selected tasks [60]: " max_selected
max_selected=${max_selected:-60}

read -r -p "Max ops per response [5]: " max_ops
max_ops=${max_ops:-5}

args=(
  --interactive
  --prompt "$prompt"
  --out "$out_path"
  --out-mode "$out_mode"
  --base-url "$base_url"
  --model "$model"
  --max-prompt-chars "$max_prompt"
  --max-selected "$max_selected"
  --max-ops "$max_ops"
)

case "$mode" in
  1)
    read -r -p "Project prefix: " project
    args+=(--project "$project")
    ;;
  2)
    read -r -p "Taskwarrior filter: " filter
    args+=(--filter "$filter")
    ;;
  3)
    read -r -p "Goal id: " goal
    read -r -p "Goals config path [scalpel/goals.json]: " goals_cfg
    goals_cfg=${goals_cfg:-scalpel/goals.json}
    args+=(--goal "$goal" --goals-config "$goals_cfg")
    ;;
  4)
    read -r -p "Default project (optional): " project
    if [[ -n "$project" ]]; then
      args+=(--project "$project")
    fi
    args+=(--new-project)
    ;;
  *)
    echo "Unknown mode: $mode"
    exit 2
    ;;
esac

python3 -m scalpel.tools.ai_plan_tasks "${args[@]}"
