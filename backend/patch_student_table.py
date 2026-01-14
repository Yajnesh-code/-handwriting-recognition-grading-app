from app import app, db
from sqlalchemy import inspect, text

def column_exists(table_name, column_name):
    inspector = inspect(db.engine)
    return column_name in [col['name'] for col in inspector.get_columns(table_name)]

with app.app_context():

    # ✅ Add batch column if missing
    if not column_exists("student", "batch"):
        print("Adding column: batch")
        db.session.execute(text("ALTER TABLE student ADD COLUMN batch TEXT DEFAULT '';"))
        db.session.commit()
    else:
        print("✅ Column 'batch' already exists")

    # ✅ Add section column if missing
    if not column_exists("student", "section"):
        print("Adding column: section")
        db.session.execute(text("ALTER TABLE student ADD COLUMN section TEXT DEFAULT '';"))
        db.session.commit()
    else:
        print("✅ Column 'section' already exists")

    print("\n✅ Patch Completed Successfully!")
