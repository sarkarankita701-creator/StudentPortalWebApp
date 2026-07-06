from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired

from models import (
    CalendarEvent,
    DoubtSessionRequest,
    Material,
    PaymentRecord,
    ROLE_STUDENT,
    ROLE_SUPER_ADMIN,
    ROLE_TEACHER,
    Test,
    TestAssignment,
    TestAttempt,
    User,
    event_assignments,
)

auth_bp = Blueprint("auth", __name__)


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In")


@auth_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.strip()).first()
        if user and user.is_active_flag and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for("auth.dashboard"))
        flash("Invalid username or password.", "error")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_super_admin():
        counts = {
            "teachers": User.query.filter_by(role=ROLE_TEACHER).count(),
            "students": User.query.filter_by(role=ROLE_STUDENT).count(),
            "events": CalendarEvent.query.count(),
            "materials": Material.query.count(),
            "tests": Test.query.count(),
        }
        return render_template("dashboard/admin.html", counts=counts)

    if current_user.is_teacher():
        counts = {
            "events": CalendarEvent.query.filter_by(teacher_id=current_user.id).count(),
            "materials": Material.query.filter_by(teacher_id=current_user.id).count(),
            "tests": Test.query.filter_by(teacher_id=current_user.id).count(),
            "students": User.query.filter_by(role=ROLE_STUDENT).count(),
            "pending_doubts": DoubtSessionRequest.query.filter_by(
                teacher_id=current_user.id, status="pending"
            ).count(),
        }
        return render_template("dashboard/teacher.html", counts=counts)

    now = datetime.utcnow()
    upcoming_events = (
        CalendarEvent.query.join(event_assignments)
        .filter(event_assignments.c.student_id == current_user.id, CalendarEvent.end_dt >= now)
        .order_by(CalendarEvent.start_dt)
        .limit(5)
        .all()
    )
    pending_tests = (
        TestAssignment.query.join(Test)
        .filter(TestAssignment.student_id == current_user.id, Test.is_published.is_(True))
        .all()
    )
    completed_ids = {
        a.test_id
        for a in TestAttempt.query.filter_by(student_id=current_user.id, status="completed").all()
    }
    pending_count = len([a for a in pending_tests if a.test_id not in completed_ids])
    materials_count = len(current_user.assigned_materials)
    pending_payments = PaymentRecord.query.filter_by(student_id=current_user.id, status="pending").count()

    counts = {
        "upcoming_events": upcoming_events,
        "pending_tests": pending_count,
        "materials": materials_count,
        "pending_payments": pending_payments,
    }
    return render_template("dashboard/student.html", counts=counts)
