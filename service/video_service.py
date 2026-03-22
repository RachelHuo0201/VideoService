from pathlib import Path
import subprocess
import shutil
import yaml
import time
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
TEMP_CONFIG_DIR = BASE_DIR / "temp_configs"
CHARACTER_DIR = BASE_DIR / "characters"

TEMP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CHARACTER_DIR.mkdir(parents=True, exist_ok=True)

# 用 v2 默认的 prompt config
BASE_PROMPT_CONFIG = BASE_DIR / "configs" / "prompts" / "infer_acc.yaml"

# 先固定用一个官方/现成 pose 目录
DEFAULT_POSE_DIR = BASE_DIR / "assets" / "halfbody_demo" / "pose" / "01"


def get_character_image(character_id: str) -> Path:
    for ext in [".png", ".jpg", ".jpeg", ".webp"]:
        candidate = CHARACTER_DIR / f"{character_id}{ext}"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"No character image found for character_id={character_id}")


def build_temp_yaml(task_id: str, image_path: Path, audio_path: Path, pose_dir: Path | None = None) -> Path:
    config_path = TEMP_CONFIG_DIR / f"{task_id}.yaml"

    if pose_dir is None:
        pose_dir = DEFAULT_POSE_DIR

    if not BASE_PROMPT_CONFIG.exists():
        raise FileNotFoundError(f"Prompt config not found: {BASE_PROMPT_CONFIG}")

    if not pose_dir.exists():
        raise FileNotFoundError(f"Pose dir not found: {pose_dir}")

    with open(BASE_PROMPT_CONFIG, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)

    # 保留原配置，只覆盖 test_cases
    config_data["test_cases"] = {
        str(image_path): [
            str(audio_path),
            str(pose_dir)
        ]
    }

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config_data, f, allow_unicode=True, sort_keys=False)

    return config_path


def find_latest_output_file(after_ts: float) -> Path:
    output_root = BASE_DIR / "output"
    if not output_root.exists():
        raise FileNotFoundError("EchoMimicV2 output directory does not exist.")

    candidates = []
    for p in output_root.rglob("*_sig.mp4"):
        if p.stat().st_mtime >= after_ts:
            candidates.append(p)

    if not candidates:
        raise FileNotFoundError("Cannot find generated *_sig.mp4 output file.")

    candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return candidates[0]


def run_echomimic_job(
    task_id: str,
    image_path: Path,
    audio_path: Path,
    output_dir: Path,
    pose_dir: Path | None = None
) -> Path:
    config_path = build_temp_yaml(
        task_id=task_id,
        image_path=image_path,
        audio_path=audio_path,
        pose_dir=pose_dir
    )

    start_ts = time.time()

    cmd = [
        sys.executable,
        "infer_acc.py",
        "--config", str(config_path),
        "-W", "768",
        "-H", "768",
        "--fps", "24",
        "--steps", "6"
    ]

    result = subprocess.run(
        cmd,
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            "EchoMimicV2 failed:\n"
            f"STDOUT:\n{result.stdout}\n\n"
            f"STDERR:\n{result.stderr}"
        )

    generated_file = find_latest_output_file(after_ts=start_ts)

    output_dir.mkdir(parents=True, exist_ok=True)
    final_video_path = output_dir / f"{task_id}.mp4"
    shutil.copy(generated_file, final_video_path)

    return final_video_path