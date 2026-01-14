from flask import Blueprint, request, jsonify
from database import db
from models.student import Student

student = Blueprint("student", __name__)

# Add Student
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

    existing = Student.query.filter_by(usn=usn).first()
    if existing:
        return jsonify({"error": "Student already exists"}), 400

    new_student = Student(
        usn=usn,
        name=name,
        department=department,
        batch=batch,
        section=section,
    )
    
    db.session.add(new_student)
    db.session.commit()

    return jsonify({"message": "Student added successfully"}), 201



# List All Students
@student.route("/list", methods=["GET"])
def list_students():
    students = Student.query.all()
    students_data = [
        {"usn": s.usn, "name": s.name, "department": s.department}
        for s in students
    ]
    return jsonify({"students": students_data}), 200


# Student Details + Results
@student.route("/<usn>", methods=["GET"])
def get_student(usn):
    from models.result import Result
    from models.exam import Exam

    usn = usn.strip().upper()
    student_record = Student.query.filter_by(usn=usn).first()
    if not student_record:
        return jsonify({"error": "Student not found"}), 404

    results = Result.query.filter_by(usn=usn).all()
    formatted_results = []
    for r in results:
        exam = Exam.query.filter_by(id=r.exam_id).first()
        formatted_results.append({
            "exam_code": exam.exam_code if exam else "",
            "score": r.score,
            "percentage": r.percentage,
            "timestamp": r.timestamp
        })

    return jsonify({
        "usn": student_record.usn,
        "name": student_record.name,
        "department": student_record.department,
        "results": formatted_results
    }), 200
