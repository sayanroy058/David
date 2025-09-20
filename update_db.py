from app import app
from models import db, Certificate
import sqlite3

with app.app_context():
    # Connect directly to SQLite database
    db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if 'course_name' column exists
    cursor.execute("PRAGMA table_info(certificates);")
    columns = [col[1] for col in cursor.fetchall()]

    if 'course_name' not in columns:
        print("⚡ Adding 'course_name' column to certificates table...")
        cursor.execute("ALTER TABLE certificates ADD COLUMN course_name TEXT;")
        conn.commit()
        print("✅ Column 'course_name' added.")
    else:
        print("ℹ️ Column 'course_name' already exists, skipping ALTER TABLE.")

    # Migrate old data if needed
    try:
        certificates = Certificate.query.all()
        for cert in certificates:
            # For offline certificates, fill course_name from old logic (if needed)
            if cert.is_offline and not cert.course_name and cert.course:
                cert.course_name = cert.course.title
        db.session.commit()
        print("✅ Data migration completed for certificates.")
    except Exception as e:
        print("⚠️ Migration skipped or failed:", e)

    conn.close()
