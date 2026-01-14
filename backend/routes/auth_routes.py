# backend/routes/auth_routes.py
from flask import Blueprint, request, jsonify
from database import db
from models.teacher import Teacher
from utils.jwt_manager import create_token

auth = Blueprint("auth", __name__)

@auth.post("/register")
def register():
    data = request.get_json() or {}
    t = Teacher(
        name=data["name"],
        college_id=data["college_id"],
        email=data["email"].lower(),
    )
    t.set_password(data["password"])
    db.session.add(t)
    db.session.commit()
    return jsonify({"message": "Registered Successfully"}), 201

@auth.post("/login")
def login():
    data = request.get_json() or {}
    t = Teacher.query.filter_by(email=data["email"].lower()).first()
    if not t or not t.check_password(data["password"]):
        return jsonify({"error": "Invalid Credentials"}), 401
    token = create_token(t.id)
    return jsonify({"token": token, "teacher": {"name": t.name, "college_id": t.college_id}})
