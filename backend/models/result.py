from database import db
from datetime import datetime

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usn = db.Column(db.String(20), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'))
    score = db.Column(db.Integer)
    percentage = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
