import os
import json
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

from mcq_recognition import process_mcq_image

# DB + AUTH
from database import db
from routes.auth_routes import auth
from routes.student_routes import student
from routes.exam_routes import exam
from routes.result_routes import result

from flask_cors import CORS

# =====================================================
# BASE DIRECTORY (CRITICAL FOR CLOUD)
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =====================================================
# FOLDERS (CLOUD-SAFE)
# =====================================================
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')
ANSWER_KEY_FOLDER = os.path.join(BASE_DIR, 'answer_keys')
RESULTS_FOLDER = os.path.join(BASE_DIR, 'results')
STUDENTS_FOLDER = os.path.join(BASE_DIR, 'students')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app = Flask(__name__)
CORS(app)

# =====================================================
# DATABASE CONFIG (CLOUD-SAFE SQLITE)
# =====================================================
db_path = os.path.join(BASE_DIR, "mcq_system.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

with app.app_context():
    db.create_all()

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
os.makedirs(ANSWER_KEY_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)
os.makedirs(STUDENTS_FOLDER, exist_ok=True)

# =====================================================
# HELPERS
# =====================================================
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# =====================================================
# HEALTH CHECK (REQUIRED FOR RENDER)
# =====================================================
@app.route("/health")
def health():
    return jsonify({"status": "ok"})

# =====================================================
# SAVE / UPDATE ANSWER KEY
# =====================================================
@app.route('/upload_answer_key', methods=['POST'])
def upload_answer_key():
    data = request.get_json()
    exam_code = data.get("exam_code", "").strip().upper()
    answer_key = data.get("answer_key")

    if not exam_code or not answer_key:
        return jsonify({"error": "exam_code and answer_key required"}), 400

    path = os.path.join(ANSWER_KEY_FOLDER, f"{exam_code}.json")
    with open(path, "w") as f:
        json.dump(answer_key, f, indent=2)

    return jsonify({"message": "Answer key saved successfully"})

# =====================================================
# GRADE EXAM
# =====================================================
@app.route('/grade', methods=['POST'])
def grade_exam():
    if 'image' not in request.files:
        return jsonify({"error": "No image file"}), 400

    usn = request.form.get("usn", "").upper()
    exam_code = request.form.get("exam_code", "").upper()

    if not usn or not exam_code:
        return jsonify({"error": "usn and exam_code required"}), 400

    key_path = os.path.join(ANSWER_KEY_FOLDER, f"{exam_code}.json")
    if not os.path.exists(key_path):
        return jsonify({"error": f"No answer key found for exam {exam_code}"}), 400

    file = request.files['image']
    if not allowed_file(file.filename):
        return jsonify({"error": "Allowed: png, jpg, jpeg"}), 400

    file_path = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
    file.save(file_path)

    results = process_mcq_image(file_path, exam_code)
    if "error" in results:
        return jsonify(results), 400

    with open(key_path, "r") as f:
        results["answer_key"] = json.load(f)

    results["usn"] = usn
    results["exam_code"] = exam_code

    student_folder = os.path.join(RESULTS_FOLDER, usn)
    os.makedirs(student_folder, exist_ok=True)

    with open(os.path.join(student_folder, f"{exam_code}.json"), "w") as f:
        json.dump(results, f, indent=2)

    return jsonify(results)

# =====================================================
# VIEW RESULT
# =====================================================
@app.route('/results/<usn>/<exam_code>', methods=['GET'])
def get_results(usn, exam_code):
    path = os.path.join(RESULTS_FOLDER, usn.upper(), f"{exam_code.upper()}.json")
    if not os.path.exists(path):
        return jsonify({"error": "Result not found"}), 404
    return jsonify(json.load(open(path)))

# =====================================================
# EXPORT PDF
# =====================================================
from reportlab.pdfgen import canvas

@app.route('/export_pdf/<usn>/<exam_code>')
def export_pdf(usn, exam_code):
    usn = usn.upper()
    exam_code = exam_code.upper()

    result_file = os.path.join(RESULTS_FOLDER, usn, f"{exam_code}.json")
    if not os.path.exists(result_file):
        return jsonify({"error": "No result found"}), 404

    data = json.load(open(result_file))
    answer_key = data["answer_key"]

    pdf_path = os.path.join(STATIC_FOLDER, f"{usn}_{exam_code}.pdf")
    c = canvas.Canvas(pdf_path)

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 780, "MCQ Result Report")
    c.setFont("Helvetica", 13)
    c.drawString(50, 750, f"USN: {usn}")
    c.drawString(50, 730, f"Exam: {exam_code}")
    c.drawString(50, 710, f"Score: {data['score']} / {data['total']} ({data['percentage']}%)")

    y = 680
    for row in data["results"]:
        q = row["question_pred"]
        c_ans = answer_key.get(q, "-")
        c.drawString(50, y, f"Q{q} Your: {row['option_pred']} Correct: {c_ans} Status: {row['result']}")
        y -= 18

    c.save()
    return send_from_directory(STATIC_FOLDER, f"{usn}_{exam_code}.pdf")

# =====================================================
# SERVE STATIC FILES
# =====================================================
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(STATIC_FOLDER, filename)

# =====================================================
# LOCAL RUN ONLY (RENDER USES GUNICORN)
# =====================================================
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
