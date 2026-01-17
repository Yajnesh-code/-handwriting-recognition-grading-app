# backend/routes/result_routes.py

from flask import Blueprint, jsonify, request, send_file
from database import db
from utils.jwt_manager import decode_token
import pandas as pd
import os

result = Blueprint("result", __name__)

# =====================================================
# AUTH HELPER
# =====================================================
def auth_required(req):
    token = req.headers.get("Authorization", "").replace("Bearer ", "")

    # ✅ allow token via query (Excel / PDF)
    if not token:
        token = req.args.get("token", "")

    try:
        return decode_token(token)["teacher_id"]
    except:
        return None


# =====================================================
# ✅ 1) GET ALL RESULTS OF A STUDENT (TEACHER SAFE)
# =====================================================
@result.get("/student/<usn>")
def get_student_results(usn):
    teacher_id = auth_required(request)
    if not teacher_id:
        return jsonify({"error": "Unauthorized"}), 401

    usn = usn.strip().upper()

    rows = list(db.results.find(
        {"usn": usn, "teacher_id": teacher_id},
        {"_id": 0}
    ))

    return jsonify({"results": rows}), 200


# =====================================================
# ✅ 2) GET ONE EXAM RESULT OF A STUDENT
# =====================================================
@result.get("/student/<usn>/<exam_code>")
def get_student_exam_result(usn, exam_code):
    teacher_id = auth_required(request)
    if not teacher_id:
        return jsonify({"error": "Unauthorized"}), 401

    usn = usn.strip().upper()
    exam_code = exam_code.strip().upper()

    data = db.results.find_one(
        {
            "usn": usn,
            "exam_code": exam_code,
            "teacher_id": teacher_id
        },
        {"_id": 0}
    )

    if not data:
        return jsonify({"error": "Result not found"}), 404

    return jsonify(data), 200


# =====================================================
# ✅ HELPER: STUDENT META
# =====================================================
def _student_meta(usn):
    stu = db.students.find_one({"usn": usn})
    if not stu:
        return {
            "name": "",
            "department": "",
            "batch": "",
            "section": ""
        }

    return {
        "name": stu.get("name", ""),
        "department": stu.get("department", ""),
        "batch": stu.get("batch", ""),
        "section": stu.get("section", "")
    }


# =====================================================
# ✅ 3) CLASS RESULTS (JSON) – TEACHER SAFE
# =====================================================
@result.get("/class_results/<exam_code>")
def class_results(exam_code):
    teacher_id = auth_required(request)
    if not teacher_id:
        return jsonify({"error": "Unauthorized"}), 401

    exam_code = exam_code.upper()
    rows = []

    for r in db.results.find({
        "exam_code": exam_code,
        "teacher_id": teacher_id
    }):
        meta = _student_meta(r["usn"])

        rows.append({
            "usn": r["usn"],
            "name": meta["name"],
            "department": meta["department"],
            "batch": meta["batch"],
            "section": meta["section"],
            "score": r.get("score", 0),
            "total": r.get("total", 0),
            "percentage": r.get("percentage", 0),
        })

    return jsonify({"results": rows}), 200


# =====================================================
# ✅ 4) EXPORT CLASS RESULT → EXCEL (SECURE)
# =====================================================
@result.get("/export_class/<exam_code>")
def export_class(exam_code):
    teacher_id = auth_required(request)
    if not teacher_id:
        return jsonify({"error": "Unauthorized"}), 401

    exam_code = exam_code.upper()
    rows = []

    for r in db.results.find({
        "exam_code": exam_code,
        "teacher_id": teacher_id
    }):
        meta = _student_meta(r["usn"])
        rows.append([
            r["usn"],
            meta["name"],
            meta["department"],
            meta["batch"],
            meta["section"],
            r.get("score", 0),
            r.get("total", 0),
            r.get("percentage", 0),
        ])

    if not rows:
        return jsonify({"error": "No results found"}), 404

    df = pd.DataFrame(
        rows,
        columns=[
            "USN", "Name", "Department", "Batch",
            "Section", "Score", "Total", "Percentage"
        ]
    )

    os.makedirs("static", exist_ok=True)
    out_path = f"static/{exam_code}_class_results.xlsx"
    df.to_excel(out_path, index=False)

    return send_file(out_path, as_attachment=True)


# =====================================================
# ✅ 5) ALL RESULTS (DEBUG / ADMIN ONLY)
# =====================================================
@result.get("/all_results")
def all_results():
    teacher_id = auth_required(request)
    if not teacher_id:
        return jsonify({"error": "Unauthorized"}), 401

    rows = list(db.results.find(
        {"teacher_id": teacher_id},
        {"_id": 0}
    ))

    return jsonify({"results": rows}), 200


# =====================================================
# ✅ 6) PDF REPORT (STUDENT – TEACHER SAFE)
# =====================================================
@result.get("/pdf/<usn>/<exam_code>")
def generate_pdf(usn, exam_code):
    
    from reportlab.pdfgen import canvas

    usn = usn.strip().upper()
    exam_code = exam_code.strip().upper()

    data = db.results.find_one({
    "usn": usn,
    "exam_code": exam_code
})


    if not data:
        return jsonify({"error": "Result not found"}), 404

    os.makedirs("static", exist_ok=True)
    out = f"static/{usn}_{exam_code}_report.pdf"
    c = canvas.Canvas(out)

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, 800, f"Report Card - {exam_code}")
    c.drawString(50, 770, f"Student: {usn}")

    c.setFont("Helvetica", 14)
    c.drawString(50, 740, f"Score: {data['score']} / {data['total']}")
    c.drawString(50, 720, f"Percentage: {data['percentage']}%")

    c.setFont("Helvetica", 12)
    y = 690
    for r in data["results"]:
        c.drawString(
            50, y,
            f"Q{r['question_pred']}: Your = {r['option_pred']} | {r['result']}"
        )
        y -= 18
        if y < 50:
            c.showPage()
            y = 800

    c.save()
    return send_file(out, as_attachment=True)
