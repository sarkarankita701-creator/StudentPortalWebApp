from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import login_required
from werkzeug.utils import secure_filename

from extensions import db
from models import ROLE_STUDENT, ROLE_SUPER_ADMIN, ROLE_TEACHER, PaymentRecord, Setting, User
from utils.decorators import role_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/users")
@login_required
@role_required(ROLE_SUPER_ADMIN)
def users():
    teachers = User.query.filter_by(role=ROLE_TEACHER).order_by(User.name).all()
    students = User.query.filter_by(role=ROLE_STUDENT).order_by(User.name).all()
    return render_template("admin/users.html", teachers=teachers, students=students)


@admin_bp.route("/users/new", methods=["POST"])
@login_required
@role_required(ROLE_SUPER_ADMIN)
def create_user():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role")

    if role not in (ROLE_TEACHER, ROLE_STUDENT):
        flash("Invalid role.", "error")
        return redirect(url_for("admin.users"))

    if not name or not username or not password:
        flash("Name, username, and password are required.", "error")
        return redirect(url_for("admin.users"))

    if User.query.filter_by(username=username).first():
        flash(f"Username '{username}' is already taken.", "error")
        return redirect(url_for("admin.users"))

    user = User(name=name, email=email, username=username, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    flash(f"{role.capitalize()} account created for {name}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@role_required(ROLE_SUPER_ADMIN)
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == ROLE_SUPER_ADMIN:
        flash("Cannot deactivate a Super Admin account.", "error")
        return redirect(url_for("admin.users"))
    user.is_active_flag = not user.is_active_flag
    db.session.commit()
    flash(f"{user.name} is now {'active' if user.is_active_flag else 'inactive'}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/settings", methods=["GET", "POST"])
@login_required
@role_required(ROLE_SUPER_ADMIN)
def settings():
    if request.method == "POST":
        price = request.form.get("default_price", "").strip()
        if price:
            try:
                float(price)
                Setting.set("default_price_per_session", price)
            except ValueError:
                flash("Default price must be a number.", "error")
                return redirect(url_for("admin.settings"))

        qr_file = request.files.get("qr_code")
        if qr_file and qr_file.filename:
            filename = secure_filename(qr_file.filename)
            if not filename.lower().endswith((".png", ".jpg", ".jpeg")):
                flash("QR code image must be a PNG or JPG file.", "error")
                return redirect(url_for("admin.settings"))
            qr_file.save(current_app.config["QR_CODE_PATH"])

        flash("Settings updated.", "success")
        return redirect(url_for("admin.settings"))

    default_price = Setting.get("default_price_per_session", str(current_app.config["DEFAULT_PRICE_PER_SESSION"]))
    return render_template("admin/settings.html", default_price=default_price)


@admin_bp.route("/finance")
@login_required
@role_required(ROLE_SUPER_ADMIN)
def finance():
    records = PaymentRecord.query.all()

    total_collected = sum(r.amount for r in records if r.status == "paid")
    total_awaiting = sum(r.amount for r in records if r.status == "awaiting_verification")
    total_pending = sum(r.amount for r in records if r.status == "pending")

    summary = {
        "total_collected": total_collected,
        "total_awaiting": total_awaiting,
        "total_pending": total_pending,
        "total_outstanding": total_awaiting + total_pending,
        "transaction_count": len(records),
        "paid_count": len([r for r in records if r.status == "paid"]),
        "awaiting_count": len([r for r in records if r.status == "awaiting_verification"]),
        "pending_count": len([r for r in records if r.status == "pending"]),
    }
    recent_records = (
        PaymentRecord.query.order_by(PaymentRecord.created_at.desc()).limit(10).all()
    )
    return render_template("admin/finance.html", summary=summary, recent_records=recent_records)
