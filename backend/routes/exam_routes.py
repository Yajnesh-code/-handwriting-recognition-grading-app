from flask import Blueprint, request, jsonify
from database import db
from models.exam import Exam
from models.answer_key import AnswerKey
from utils.jwt_manager import decode_token

exam = Blueprint("exam", __name__)

def auth_required(req):
    token = req.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        return decode_token(token)["teacher_id"]
    except:
        return None


# ✅ Create an exam
@exam.post("/create")
def create_exam():
    teacher_id = auth_required(request)
    if not teacher_id:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    exam_code = data.get("exam_code", "").upper().strip()
    subject = data.get("subject", "").strip()

    if not exam_code or not subject:
        return jsonify({"error": "exam_code and subject required"}), 400

    if Exam.query.filter_by(exam_code=exam_code).first():
        return jsonify({"error": "Exam already exists"}), 409

    e = Exam(exam_code=exam_code, subject=subject, teacher_id=teacher_id)
    db.session.add(e)
    db.session.commit()

    return jsonify({"message": "Exam Created"}), 201


# ✅ Save answer key (10 questions)
@exam.post("/save_key")
def save_key():
    teacher_id = auth_required(request)
    if not teacher_id:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    exam_code = data.get("exam_code", "").upper().strip()
    answers = data.get("answer_key", {})

    exam_obj = Exam.query.filter_by(exam_code=exam_code, teacher_id=teacher_id).first()
    if not exam_obj:
        return jsonify({"error": "Exam not found or unauthorized"}), 404

    # Clear old key
    AnswerKey.query.filter_by(exam_id=exam_obj.id).delete()

    # Save new key
    for q, opt in answers.items():
        db.session.add(AnswerKey(exam_id=exam_obj.id, question_no=q, correct_option=opt))

    db.session.commit()
    return jsonify({"message": "Answer Key Saved"}), 200


# ✅ Get existing key
@exam.get("/get_key/<exam_code>")
def get_key(exam_code):
    exam_code = exam_code.upper()
    exam_obj = Exam.query.filter_by(exam_code=exam_code).first()
    if not exam_obj:
        return jsonify({"error": "Exam not found"}), 404

    key = AnswerKey.query.filter_by(exam_id=exam_obj.id).all()
    result = {k.question_no: k.correct_option for k in key}

    return jsonify({"answer_key": result})
