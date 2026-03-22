from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path
import uuid
import traceback

from service.tts_service import fetch_tts_audio
from service.video_service import run_echomimic_job, get_character_image

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
MEDIA_DIR = BASE_DIR / "outputs_api"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"message": "video service is running"}), 200

@app.route("/generate_video", methods=["POST"])
def generate_video():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "missing json body"}), 400

        character_id = data.get("character_id")
        reply_text = data.get("reply_text")
        language = data.get("language", "en")

        if not character_id:
            return jsonify({"error": "missing character id"}), 400
        if not reply_text:
            return jsonify({"error": "missing reply text"}), 400

        task_id = str(uuid.uuid4())
        image_path = get_character_image(character_id)
        audio_path = fetch_tts_audio(
            reply_text=reply_text,
            task_id=task_id,
            output_dir=MEDIA_DIR,
            language=language
        )
        video_path = run_echomimic_job(
            task_id=task_id,
            image_path=image_path,
            audio_path=audio_path,
            output_dir=MEDIA_DIR
        )

        return jsonify({
            "message": "success",
            "task_id": task_id,
            "audio_url": f"/media/{audio_path.name}",
            "video_url": f"/media/{video_path.name}"
        }), 200

    except Exception as e:
        print("generate_video error:", e)
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route("/media/<path:filename>", methods=["GET"])
def serve_media(filename):
    return send_from_directory(str(MEDIA_DIR), filename)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)