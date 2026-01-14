# backend/models/exam.py
from database import db

class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_code = db.Column(db.String(20), unique=True, nullable=False)
    subject = db.Column(db.String(120), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teacher.id"), nullable=False)
