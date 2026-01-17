from dotenv import load_dotenv
load_dotenv()

import os
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from datetime import datetime
from utils.jwt_manager import decode_token

from mcq_recognition import process_mcq_image
from database import db

from routes.auth_routes import auth
from routes.student_routes import student
from routes.exam_routes import exam
from routes.result_routes import result

from flask_cors import CORS

# =====================================================
# BASE DIRECTORY
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
STATIC_FOLDER = os.path.join(BASE_DIR, "static")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

app = Flask(__name__)
CORS(app)

# =====================================================
# BLUEPRINTS
# =====================================================
app.register_blueprint(auth, url_prefix="/auth")
app.register_blueprint(student, url_prefix="/student")
app.register_blueprint(exam, url_prefix="/exam")
app.register_blueprint(result, url_prefix="/result")

# =====================================================
# CREATE RUNTIME FOLDERS
# =====================================================
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)

# =====================================================
# HELPERS
# =====================================================
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# =====================================================
# HEALTH CHECK
# =====================================================
@app.get("/health")
def health():
    return jsonify({"status": "ok"})

# =====================================================
# GRADE EXAM  ✅ (FINAL FIXED VERSION)
# =====================================================
@app.post("/grade")
def grade_exam():
    if "image" not in request.files:
        return jsonify({"error": "No image file"}), 400

    usn = request.form.get("usn", "").strip().upper()
    exam_code = request.form.get("exam_code", "").strip().upper()

    if not usn or not exam_code:
        return jsonify({"error": "usn and exam_code required"}), 400

    # 🔐 AUTH (ONLY VALIDATE TOKEN)
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        decode_token(token)
    except:
        return jsonify({"error": "Unauthorized"}), 401

    # ✅ FETCH ANSWER KEY FROM MONGODB (ONLY ONCE)
    key_doc = db.answer_keys.find_one({"exam_code": exam_code})
    if not key_doc:
        return jsonify({"error": "Answer key not found"}), 404

    file = request.files["image"]
    if not allowed_file(file.filename):
        return jsonify({"error": "Allowed: png, jpg, jpeg"}), 400

    file_path = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
    file.save(file_path)

    # ✅ PASS ANSWER KEY DIRECTLY
    results = process_mcq_image(
    file_path,
    key_doc["answer_key"]
)


    if "error" in results:
        return jsonify(results), 400

    # METADATA
    results["usn"] = usn
    results["exam_code"] = exam_code
    results["timestamp"] = datetime.utcnow()

    # SAVE RESULT
    db.results.replace_one(
        {"usn": usn, "exam_code": exam_code},
        results,
        upsert=True
    )

    return jsonify(results), 200

# =====================================================
# STATIC FILES
# =====================================================
@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(STATIC_FOLDER, filename)

# =====================================================
# LOCAL RUN
# =====================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
