# backend/database.py
from pymongo import MongoClient
import os

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://mediconnect_user:Yajju%40897177@cluster0.kw0myb4.mongodb.net/?appName=Cluster0"
)

client = MongoClient(MONGO_URI)

# DATABASE (auto-created)
db = client["mcq_grading_db"]

# COLLECTIONS
users_col = db["users"]        # teachers
students_col = db["students"]
exams_col = db["exams"]
results_col = db["results"]
answer_keys_col = db["answer_keys"]
