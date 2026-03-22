from pathlib import Path
import requests

TTS_URL = "http://127.0.0.1:5001"

def fetch_tts_audio(reply_text: str, task_id: str, output_dir: Path, language: str = "en") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{task_id}.wav"

    url = f"{TTS_URL}/tts_to_file"
    payload = {
        "text": reply_text,
        "language": language
    }

    response = requests.post(url, json=payload, stream=True, timeout=120)

    if response.status_code != 200:
        raise RuntimeError(
            f"TTS request failed: status={response.status_code}, body={response.text}"
        )

    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    return output_path