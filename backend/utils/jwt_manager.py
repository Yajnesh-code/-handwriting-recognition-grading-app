# backend/utils/jwt_manager.py
import jwt
from datetime import datetime, timedelta

SECRET = "CHANGE_THIS_SECRET"

def create_token(teacher_id):
    payload = {"teacher_id": teacher_id, "exp": datetime.utcnow() + timedelta(hours=8)}
    return jwt.encode(payload, SECRET, algorithm="HS256")

def decode_token(token):
    return jwt.decode(token, SECRET, algorithms=["HS256"])
