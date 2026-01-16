# backend/database.py
from pymongo import MongoClient
import os

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise RuntimeError("MONGO_URI environment variable not set")

client = MongoClient(MONGO_URI)
# DATABASE (auto-created)
db = client["mcq_grading_db"]

# COLLECTIONS
users_col = db["users"]        # teachers
students_col = db["students"]
exams_col = db["exams"]
results_col = db["results"]
answer_keys_col = db["answer_keys"]
