from app import app, db, Admin
from werkzeug.security import generate_password_hash

# --------------- CONFIG -----------------
NEW_PASSWORD = "smart123"  # <- change this

with app.app_context():
    admin = Admin.query.first()
    if admin:
        admin.password = generate_password_hash(NEW_PASSWORD)
        db.session.commit()
        print(f"✅ Admin password changed to: {NEW_PASSWORD}")
    else:
        print("⚠️ No admin user found.")