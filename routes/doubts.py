from datetime import datetime, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import ROLE_STUDENT, ROLE_SUPER_ADMIN, ROLE_TEACHER, CalendarEvent, DoubtSessionRequest, User
from utils.decorators import role_required

doubts_bp = Blueprint("doubts", __name__, url_prefix="/doubts")


@doubts_bp.route("/")
@login_required
def view():
    if current_user.is_student():
        requests_ = (
            DoubtSessionRequest.query.filter_by(student_id=current_user.id)
            .order_by(DoubtSessionRequest.created_at.desc())
            .all()
        )
        return render_template("doubts/student_list.html", requests=requests_)

    if current_user.is_teacher():
        requests_ = (
            DoubtSessionRequest.query.filter_by(teacher_id=current_user.id)
            .order_by(DoubtSessionRequest.created_at.desc())
            .all()
        )
        pending = [r for r in requests_ if r.status == "pending"]
        resolved = [r for r in requests_ if r.status != "pending"]
        return render_template("doubts/teacher_list.html", pending=pending, resolved=resolved)

    requests_ = DoubtSessionRequest.query.order_by(DoubtSessionRequest.created_at.desc()).all()
    return render_template("doubts/admin_list.html", requests=requests_)


@doubts_bp.route("/new", methods=["GET", "POST"])
@login_required
@role_required(ROLE_STUDENT)
def new_request():
    teachers = User.query.filter_by(role=ROLE_TEACHER, is_active_flag=True).order_by(User.name).all()

    if request.method == "POST":
        teacher_id = request.form.get("teacher_id", type=int)
        topic = request.form.get("topic", "").strip()
        proposed_raw = request.form.get("proposed_dt")
        duration_minutes = request.form.get("duration_minutes", type=int)

        teacher = next((t for t in teachers if t.id == teacher_id), None)
        if not teacher or not topic or not proposed_raw or duration_minutes not in (30, 45, 60):
            flash("Teacher, topic, proposed time, and a valid duration are required.", "error")
            return render_template("doubts/form.html", teachers=teachers)

        try:
            proposed_dt = datetime.fromisoformat(proposed_raw)
        except ValueError:
            flash("Invalid date/time format.", "error")
            return render_template("doubts/form.html", teachers=teachers)

        doubt_request = DoubtSessionRequest(
            student_id=current_user.id,
            teacher_id=teacher.id,
            topic=topic,
            proposed_dt=proposed_dt,
            duration_minutes=duration_minutes,
        )
        db.session.add(doubt_request)
        db.session.commit()
        flash("Doubt session request sent. You'll be notified once your teacher responds.", "success")
        return redirect(url_for("doubts.view"))

    return render_template("doubts/form.html", teachers=teachers)


def _get_owned_request(request_id):
    doubt_request = DoubtSessionRequest.query.get_or_404(request_id)
    if doubt_request.teacher_id != current_user.id:
        abort(403)
    return doubt_request


@doubts_bp.route("/<int:request_id>/approve", methods=["POST"])
@login_required
@role_required(ROLE_TEACHER)
def approve_request(request_id):
    doubt_request = _get_owned_request(request_id)
    if doubt_request.status != "pending":
        flash("This request has already been resolved.", "error")
        return redirect(url_for("doubts.view"))

    end_dt = doubt_request.proposed_dt + timedelta(minutes=doubt_request.duration_minutes)
    event = CalendarEvent(
        title=f"Doubt Session: {doubt_request.topic[:100]}",
        subject="Doubt Clearing Session",
        teacher_id=current_user.id,
        meet_url=current_user.default_meet_url or "",
        start_dt=doubt_request.proposed_dt,
        end_dt=end_dt,
    )
    event.students = [doubt_request.student]
    db.session.add(event)
    db.session.flush()

    doubt_request.status = "approved"
    doubt_request.resolved_at = datetime.utcnow()
    doubt_request.calendar_event_id = event.id
    db.session.commit()

    flash("Request approved and added to the calendar.", "success")
    return redirect(url_for("doubts.view"))


@doubts_bp.route("/<int:request_id>/reject", methods=["POST"])
@login_required
@role_required(ROLE_TEACHER)
def reject_request(request_id):
    doubt_request = _get_owned_request(request_id)
    if doubt_request.status != "pending":
        flash("This request has already been resolved.", "error")
        return redirect(url_for("doubts.view"))

    doubt_request.status = "rejected"
    doubt_request.resolved_at = datetime.utcnow()
    db.session.commit()
    flash("Request rejected.", "success")
    return redirect(url_for("doubts.view"))
