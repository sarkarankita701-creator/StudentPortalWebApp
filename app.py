import os

from flask import Flask
from flask_migrate import upgrade
from flask_wtf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from extensions import db, login_manager, migrate
from models import User
from utils.seed import seed_super_admin


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Trust the X-Forwarded-* headers ngrok sets so Flask knows the original
    # request was HTTPS (needed for secure cookies and CSRF checks) even
    # though it only ever receives plain HTTP from the local tunnel.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    CSRFProtect(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_globals():
        from datetime import datetime

        return {"current_year": datetime.now().year}

    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.calendar import calendar_bp
    from routes.materials import materials_bp
    from routes.tests import tests_bp
    from routes.performance import performance_bp
    from routes.payments import payments_bp
    from routes.teacher import teacher_bp
    from routes.doubts import doubts_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(materials_bp)
    app.register_blueprint(tests_bp)
    app.register_blueprint(performance_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(doubts_bp)

    return app


def init_db(app):
    """Apply pending migrations (or bootstrap a brand-new DB) and seed the default admin.

    Deliberately kept out of create_app() so that `flask db migrate`/`flask db init` — which
    import this module just to inspect the app/db metadata — don't try to run migrations
    against a database that doesn't have any migration history yet.
    """
    with app.app_context():
        if os.path.isdir(os.path.join(app.root_path, "migrations")):
            upgrade()
        else:
            db.create_all()

    seed_super_admin(app)


app = create_app()

if __name__ == "__main__":
    init_db(app)
    app.run(debug=False, port=5000)
