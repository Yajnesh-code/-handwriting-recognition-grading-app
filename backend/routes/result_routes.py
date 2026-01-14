# routes/result_routes.py

from flask import Blueprint, jsonify, request, send_file
from database import db
from models.result import Result
from models.exam import Exam

import os
import json
import pandas as pd

result = Blueprint("result", __name__)

RESULTS_FOLDER = "results"


# ✅ 1) Get all results of a student
@result.route("/student/<usn>", methods=["GET"])
def get_student_results(usn):
    usn = usn.strip().upper()
    student_folder = os.path.join(RESULTS_FOLDER, usn)

    if not os.path.exists(student_folder):
        return jsonify({"message": "No results found"}), 200

    formatted = []
    for file in os.listdir(student_folder):
        if file.endswith(".json"):
            data = json.load(open(os.path.join(student_folder, file)))
            formatted.append({
                "exam_code": data.get("exam_code", ""),
                "score": data.get("score", 0),
                "percentage": data.get("percentage", 0),
                "timestamp": data.get("timestamp", "")
            })

    return jsonify({"results": formatted}), 200


# ✅ 2) Get results for a specific exam of a student
@result.route("/student/<usn>/<exam_code>", methods=["GET"])
def get_student_exam_result(usn, exam_code):
    usn = usn.strip().upper()
    exam_code = exam_code.strip().upper()

    file_path = os.path.join(RESULTS_FOLDER, usn, f"{exam_code}.json")
    if not os.path.exists(file_path):
        return jsonify({"error": "Result not found"}), 404

    data = json.load(open(file_path))
    return jsonify(data), 200


# ✅ 3) Export class result to Excel for a given exam
# ✅ Helper: fetch student info from DB safely
def _student_meta(usn):
    from models.student import Student
    stu = Student.query.filter_by(usn=usn).first()
    if not stu:
        return {"name": "", "department": "", "batch": "", "section": ""}
    return {
        "name": stu.name or "",
        "department": stu.department or "",
        "batch": stu.batch or "",
        "section": stu.section or "",
    }


# ✅ 4) Class Results JSON (for frontend list & filtering)
@result.get("/class_results/<exam_code>")
def class_results(exam_code):
    exam_code = exam_code.upper()
    rows = []

    for usn in os.listdir(RESULTS_FOLDER):
        file = os.path.join(RESULTS_FOLDER, usn, f"{exam_code}.json")
        if os.path.exists(file):
            data = json.load(open(file))
            meta = _student_meta(usn)

            rows.append({
                "usn": usn,
                "name": meta["name"],
                "department": meta["department"],
                "batch": meta["batch"],
                "section": meta["section"],
                "score": data.get("score", 0),
                "total": data.get("total", 0),
                "percentage": data.get("percentage", 0),
            })

    return jsonify({"results": rows}), 200


# ✅ 3) Excel Export — now includes filters fields too
@result.get("/export_class/<exam_code>")
def export_class(exam_code):
    exam_code = exam_code.upper()
    rows = []

    for usn in os.listdir(RESULTS_FOLDER):
        file = os.path.join(RESULTS_FOLDER, usn, f"{exam_code}.json")
        if os.path.exists(file):
            data = json.load(open(file))
            meta = _student_meta(usn)

            rows.append([
                usn,
                meta["name"],
                meta["department"],
                meta["batch"],
                meta["section"],
                data.get("score", 0),
                data.get("total", 0),
                data.get("percentage", 0),
            ])

    if not rows:
        return jsonify({"error": "No results found for this exam"}), 404

    df = pd.DataFrame(
        rows,
        columns=["USN", "Name", "Department", "Batch", "Section", "Score", "Total", "Percentage"]
    )
    out_path = f"static/{exam_code}_class_results.xlsx"
    df.to_excel(out_path, index=False)

    return send_file(out_path, as_attachment=True)

@result.get("/all_results")
def all_results():
    rows = []

    for usn in os.listdir("results"):
        folder = os.path.join("results", usn)
        if not os.path.isdir(folder):
            continue
        
        for file in os.listdir(folder):
            if file.endswith(".json"):
                data = json.load(open(os.path.join(folder, file)))
                rows.append({
                    "usn": usn,
                    "exam_code": data["exam_code"],
                    "score": data["score"],
                    "total": data["total"],
                    "percentage": data["percentage"]
                })

    return jsonify({"results": rows}), 200

# ✅ 5) Generate PDF Report for a Student's Exam
@result.route("/pdf/<usn>/<exam_code>", methods=["GET"])
def generate_pdf(usn, exam_code):
    from reportlab.pdfgen import canvas
    import json, os

    usn = usn.strip().upper()
    exam_code = exam_code.strip().upper()

    result_file = f"results/{usn}/{exam_code}.json"
    if not os.path.exists(result_file):
        return jsonify({"error": "Result not found"}), 404

    out = f"static/{usn}_{exam_code}_report.pdf"
    c = canvas.Canvas(out)

    data = json.load(open(result_file))

    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, 800, f"Report Card - {exam_code}")
    c.drawString(50, 770, f"Student: {usn}")

    c.setFont("Helvetica", 14)
    c.drawString(50, 740, f"Score: {data['score']} / {data['total']}")
    c.drawString(50, 720, f"Percentage: {data['percentage']}%")

    # Question Breakdown
    c.setFont("Helvetica", 12)
    y = 690
    for r in data["results"]:
        c.drawString(50, y, f"Q{r['question_pred']}: Your Answer = {r['option_pred']} | {r['result']}")
        y -= 18
        if y < 50:
            c.showPage()
            y = 800

    c.save()

    return send_file(out, as_attachment=True)
