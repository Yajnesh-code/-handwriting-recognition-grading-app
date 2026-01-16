# backend/routes/student_routes.py

from flask import Blueprint, request, jsonify
from database import students_col, results_col, exams_col

student = Blueprint("student", __name__)

# =====================================================
# ADD STUDENT
# =====================================================
@student.route("/add_student", methods=["POST"])
def add_student():
    data = request.get_json() or {}

    usn = data.get("usn", "").strip().upper()
    name = data.get("name", "").strip()
    department = data.get("department", "").strip()
    batch = data.get("batch", "").strip()
    section = data.get("section", "").strip()

    if not usn or not name:
        return jsonify({"error": "USN and Name are required"}), 400

    # Check duplicate
    if students_col.find_one({"usn": usn}):
        return jsonify({"error": "Student already exists"}), 400

    student_doc = {
        "usn": usn,
        "name": name,
        "department": department,
        "batch": batch,
        "section": section
    }

    students_col.insert_one(student_doc)

    return jsonify({"message": "Student added successfully"}), 201


# =====================================================
# LIST ALL STUDENTS
# =====================================================
@student.route("/list", methods=["GET"])
def list_students():
    students = students_col.find({}, {"_id": 0})

    students_data = list(students)

    return jsonify({"students": students_data}), 200


# =====================================================
# STUDENT DETAILS + RESULTS
# =====================================================
@student.route("/<usn>", methods=["GET"])
def get_student(usn):
    usn = usn.strip().upper()

    student_record = students_col.find_one({"usn": usn}, {"_id": 0})
    if not student_record:
        return jsonify({"error": "Student not found"}), 404

    results_cursor = results_col.find({"usn": usn})
    formatted_results = []

    for r in results_cursor:
        exam = exams_col.find_one({"_id": r.get("exam_id")})
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
        "results": formatted_results
    }), 200
