# backend/routes/auth_routes.py

from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import users_col
from utils.jwt_manager import create_token
from bson import ObjectId

auth = Blueprint("auth", __name__)

# =====================================================
# ✅ REGISTER TEACHER
# =====================================================
@auth.post("/register")
def register():
    data = request.get_json() or {}

    required = ["name", "college_id", "email", "password"]
    if not all(k in data for k in required):
        return jsonify({"error": "Missing fields"}), 400

    email = data["email"].lower().strip()

    # ❌ Duplicate email check
    if users_col.find_one({"email": email}):
        return jsonify({"error": "Email already registered"}), 409

    teacher_doc = {
        "name": data["name"].strip(),
        "college_id": data["college_id"].strip(),
        "email": email,
        "password_hash": generate_password_hash(data["password"]),
        "role": "teacher"  # ✅ future-proofing
    }

    users_col.insert_one(teacher_doc)

    return jsonify({"message": "Registered Successfully"}), 201


# =====================================================
# ✅ LOGIN TEACHER
# =====================================================
@auth.post("/login")
def login():
    data = request.get_json() or {}

    if "email" not in data or "password" not in data:
        return jsonify({"error": "Email and password required"}), 400

    email = data["email"].lower().strip()
    teacher = users_col.find_one({"email": email})

    if not teacher:
        return jsonify({"error": "Invalid Credentials"}), 401

    if not check_password_hash(teacher["password_hash"], data["password"]):
        return jsonify({"error": "Invalid Credentials"}), 401

    # ✅ Create JWT with teacher_id
    token = create_token(str(teacher["_id"]))

    return jsonify({
        "token": token,
        "teacher": {
            "id": str(teacher["_id"]),          # 🔑 IMPORTANT
            "name": teacher["name"],
            "college_id": teacher["college_id"],
            "email": teacher["email"],
            "role": teacher.get("role", "teacher")
        }
    }), 200
