from database import db

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usn = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(50), default="")
    batch = db.Column(db.String(10), default="")
    section = db.Column(db.String(5), default="")
