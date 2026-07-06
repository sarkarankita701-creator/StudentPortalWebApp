from extensions import db
from models import ROLE_SUPER_ADMIN, User


def seed_super_admin(app):
    with app.app_context():
        exists = User.query.filter_by(role=ROLE_SUPER_ADMIN).first()
        if exists:
            return

        admin = User(
            name=app.config["DEFAULT_SUPER_ADMIN_NAME"],
            email=app.config["DEFAULT_SUPER_ADMIN_EMAIL"],
            username=app.config["DEFAULT_SUPER_ADMIN_USERNAME"],
            role=ROLE_SUPER_ADMIN,
        )
        admin.set_password(app.config["DEFAULT_SUPER_ADMIN_PASSWORD"])
        db.session.add(admin)
        db.session.commit()

        print("=" * 60)
        print("Seeded default Super Admin account:")
        print(f"  username: {app.config['DEFAULT_SUPER_ADMIN_USERNAME']}")
        print(f"  password: {app.config['DEFAULT_SUPER_ADMIN_PASSWORD']}")
        print("Please log in and change these credentials.")
        print("=" * 60)
