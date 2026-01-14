# backend/models/answer_key.py
from database import db

class AnswerKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exam.id"), nullable=False)
    question_no = db.Column(db.String(5), nullable=False)
    correct_option = db.Column(db.String(1), nullable=False)
