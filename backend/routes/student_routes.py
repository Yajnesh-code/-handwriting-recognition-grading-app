# backend/routes/student_routes.py

from flask import Blueprint, request, jsonify
from database import students_col, results_col, exams_col
from utils.jwt_manager import decode_token

student = Blueprint("student", __name__)

# =====================================================
# AUTH HELPER – GET LOGGED-IN TEACHER
# =====================================================
def get_teacher_id(req):
    token = req.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        return decode_token(token)["teacher_id"]
    except:
        return None


# =====================================================
# ✅ ADD STUDENT (TEACHER-SCOPED)
# =====================================================
@student.route("/add_student", methods=["POST"])
def add_student():
    teacher_id = get_teacher_id(request)
    if not teacher_id:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}

    usn = data.get("usn", "").strip().upper()
    name = data.get("name", "").strip()
    department = data.get("department", "").strip()
    batch = data.get("batch", "").strip()
    section = data.get("section", "").strip()

    if not usn or not name:
        return jsonify({"error": "USN and Name are required"}), 400

    # ❌ Duplicate check PER TEACHER
    if students_col.find_one({"usn": usn, "teacher_id": teacher_id}):
        return jsonify({"error": "Student already exists"}), 400

    student_doc = {
        "usn": usn,
        "name": name,
        "department": department,
        "batch": batch,
        "section": section,
        "teacher_id": teacher_id
    }

    students_col.insert_one(student_doc)

    return jsonify({"message": "Student added successfully"}), 201


# =====================================================
# ✅ LIST STUDENTS (ONLY LOGGED-IN TEACHER)
# =====================================================
@student.route("/list", methods=["GET"])
def list_students():
    teacher_id = get_teacher_id(request)
    if not teacher_id:
        return jsonify({"error": "Unauthorized"}), 401

    students = students_col.find(
        {"teacher_id": teacher_id},
        {"_id": 0}
    )

    return jsonify({"students": list(students)}), 200


# =====================================================
# ✅ STUDENT DETAILS + RESULTS (TEACHER-SCOPED)
# =====================================================
@student.route("/<usn>", methods=["GET"])
def get_student(usn):
    teacher_id = get_teacher_id(request)
    if not teacher_id:
        return jsonify({"error": "Unauthorized"}), 401

    usn = usn.strip().upper()

    student_record = students_col.find_one(
        {"usn": usn, "teacher_id": teacher_id},
        {"_id": 0}
    )
    if not student_record:
        return jsonify({"error": "Student not found"}), 404

    results_cursor = results_col.find(
        {"usn": usn, "teacher_id": teacher_id}
    )

    formatted_results = []
    for r in results_cursor:
        exam = exams_col.find_one(
            {"exam_code": r.get("exam_code"), "teacher_id": teacher_id}
        )
        formatted_results.append({
            "exam_code": exam["exam_code"] if exam else "",
            "score": r.get("score"),
            "percentage": r.get("percentage"),
            "timestamp": r.get("timestamp")
        })

    return jsonify({
        "usn": student_record["usn"],
        "name": student_record["name"],
        "department": student_record.get("department", ""),
        "batch": student_record.get("batch", ""),
        "section": student_record.get("section", ""),
        "results": formatted_results
    }), 200


# =====================================================
# ✅ CHECK IF STUDENT EXISTS (SCAN VALIDATION)
# =====================================================
@student.get("/exists/<usn>")
def student_exists(usn):
    teacher_id = get_teacher_id(request)
    if not teacher_id:
        return jsonify({"exists": False}), 401

    usn = usn.strip().upper()

    student = students_col.find_one(
        {"usn": usn, "teacher_id": teacher_id}
    )

    if not student:
        return jsonify({"exists": False}), 404

    return jsonify({"exists": True}), 200
