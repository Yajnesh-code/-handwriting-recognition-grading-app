# backend/routes/exam_routes.py

from flask import Blueprint, request, jsonify
from database import db
from utils.jwt_manager import decode_token

exam = Blueprint("exam", __name__)

# =====================================================
# AUTH HELPER
# =====================================================
def auth_required(req):
    token = req.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        return decode_token(token)["teacher_id"]
    except:
        return None


# =====================================================
# ✅ CREATE EXAM
# =====================================================
@exam.post("/create")
def create_exam():
    teacher_id = auth_required(request)
    if not teacher_id:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
    exam_code = data.get("exam_code", "").upper().strip()
    subject = data.get("subject", "").strip()

    if not exam_code or not subject:
        return jsonify({"error": "exam_code and subject required"}), 400

    # ❌ Duplicate exam for same teacher
    if db.exams.find_one({
        "exam_code": exam_code,
        "teacher_id": teacher_id
    }):
        return jsonify({"error": "Exam already exists"}), 409

    db.exams.insert_one({
        "exam_code": exam_code,
        "subject": subject,
        "teacher_id": teacher_id
    })

    return jsonify({"message": "Exam Created"}), 201


# =====================================================
# ✅ SAVE ANSWER KEY (TEACHER SAFE)
# =====================================================
@exam.post("/save_key")
def save_key():
    teacher_id = auth_required(request)
    if not teacher_id:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
    exam_code = data.get("exam_code", "").upper().strip()
    answers = data.get("answer_key", {})

    if not exam_code or not answers:
        return jsonify({"error": "exam_code and answer_key required"}), 400

    # ✅ Verify exam belongs to teacher
    exam_obj = db.exams.find_one({
        "exam_code": exam_code,
        "teacher_id": teacher_id
    })

    if not exam_obj:
        return jsonify({"error": "Exam not found or unauthorized"}), 404

    # Replace old key
    db.answer_keys.delete_many({
        "exam_code": exam_code,
        "teacher_id": teacher_id
    })

    db.answer_keys.insert_one({
        "exam_code": exam_code,
        "answer_key": answers,
        "teacher_id": teacher_id
    })

    return jsonify({"message": "Answer Key Saved"}), 200


# =====================================================
# ✅ GET ANSWER KEY (TEACHER SAFE)
# =====================================================
@exam.get("/get_key/<exam_code>")
def get_key(exam_code):
    teacher_id = auth_required(request)
    if not teacher_id:
        return jsonify({"error": "Unauthorized"}), 401

    exam_code = exam_code.upper().strip()

    key_doc = db.answer_keys.find_one({
        "exam_code": exam_code,
        "teacher_id": teacher_id
    })

    if not key_doc:
        return jsonify({"answer_key": {}}), 200

    return jsonify({"answer_key": key_doc["answer_key"]}), 200


# =====================================================
# ✅ CHECK IF EXAM EXISTS (FIXED)
# =====================================================
@exam.get("/exists/<exam_code>")
def exam_exists(exam_code):
    teacher_id = auth_required(request)
    if not teacher_id:
        return jsonify({"exists": False}), 401

    exam_code = exam_code.upper().strip()

    exam_obj = db.exams.find_one({
        "exam_code": exam_code,
        "teacher_id": teacher_id
    })

    if not exam_obj:
        return jsonify({"exists": False}), 404

    return jsonify({"exists": True}), 200
