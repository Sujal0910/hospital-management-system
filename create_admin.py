from app import app, db, User

ADMIN_EMAIL = "admin@hospital.com"
ADMIN_PASSWORD = "admin123"


with app.app_context():
    db.create_all()
    print("Database tables created.")
    if User.query.filter_by(role='admin').first() is None:
        admin_user = User(
            email=ADMIN_EMAIL,
            role='admin'
        )
        admin_user.set_password(ADMIN_PASSWORD)
        db.session.add(admin_user)
        db.session.commit()
        print(f"Admin user created with email: {ADMIN_EMAIL}")
    else:
        print("Admin user already exists.")