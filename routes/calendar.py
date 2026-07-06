import calendar as pycal
from datetime import date, datetime, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import ROLE_STUDENT, ROLE_SUPER_ADMIN, ROLE_TEACHER, CalendarEvent, User
from utils.decorators import role_required

calendar_bp = Blueprint("calendar", __name__, url_prefix="/calendar")


@calendar_bp.route("/")
@login_required
def list_events():
    today = date.today()
    year = request.args.get("year", today.year, type=int)
    month = request.args.get("month", today.month, type=int)

    if month < 1:
        month, year = 12, year - 1
    elif month > 12:
        month, year = 1, year + 1

    month_start = datetime(year, month, 1)
    days_in_month = pycal.monthrange(year, month)[1]
    month_end = datetime(year, month, days_in_month, 23, 59, 59)

    query = CalendarEvent.query.filter(
        CalendarEvent.start_dt >= month_start, CalendarEvent.start_dt <= month_end
    )
    if current_user.is_teacher():
        query = query.filter_by(teacher_id=current_user.id)
    elif current_user.is_student():
        query = query.filter(CalendarEvent.students.any(id=current_user.id))
    events = query.order_by(CalendarEvent.start_dt).all()

    events_by_day = {}
    for e in events:
        events_by_day.setdefault(e.start_dt.day, []).append(e)

    cal = pycal.Calendar(firstweekday=0)
    weeks = cal.monthdayscalendar(year, month)

    prev_month, prev_year = (12, year - 1) if month == 1 else (month - 1, year)
    next_month, next_year = (1, year + 1) if month == 12 else (month + 1, year)

    return render_template(
        "calendar/list.html",
        weeks=weeks,
        events_by_day=events_by_day,
        month_name=pycal.month_name[month],
        year=year,
        month=month,
        prev_month=prev_month,
        prev_year=prev_year,
        next_month=next_month,
        next_year=next_year,
        today=today,
    )


@calendar_bp.route("/new", methods=["GET", "POST"])
@login_required
@role_required(ROLE_TEACHER, ROLE_SUPER_ADMIN)
def new_event():
    students = User.query.filter_by(role=ROLE_STUDENT, is_active_flag=True).order_by(User.name).all()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        subject = request.form.get("subject", "").strip()
        meet_url = request.form.get("meet_url", "").strip()
        start_raw = request.form.get("start_dt")
        duration_minutes = request.form.get("duration_minutes", type=int)
        student_ids = request.form.getlist("student_ids")

        if not title or not start_raw or duration_minutes not in (30, 45, 60):
            flash("Title, start time, and a valid duration are required.", "error")
            return render_template("calendar/form.html", students=students)

        try:
            start_dt = datetime.fromisoformat(start_raw)
        except ValueError:
            flash("Invalid date/time format.", "error")
            return render_template("calendar/form.html", students=students)

        end_dt = start_dt + timedelta(minutes=duration_minutes)

        event = CalendarEvent(
            title=title,
            subject=subject,
            teacher_id=current_user.id,
            meet_url=meet_url,
            start_dt=start_dt,
            end_dt=end_dt,
        )
        if student_ids:
            event.students = User.query.filter(User.id.in_(student_ids)).all()

        db.session.add(event)
        db.session.commit()
        flash("Session scheduled.", "success")
        return redirect(url_for("calendar.list_events", year=start_dt.year, month=start_dt.month))

    return render_template("calendar/form.html", students=students)


@calendar_bp.route("/<int:event_id>/delete", methods=["POST"])
@login_required
@role_required(ROLE_TEACHER, ROLE_SUPER_ADMIN)
def delete_event(event_id):
    event = CalendarEvent.query.get_or_404(event_id)
    if current_user.is_teacher() and event.teacher_id != current_user.id:
        abort(403)
    db.session.delete(event)
    db.session.commit()
    flash("Session removed.", "success")
    return redirect(url_for("calendar.list_events"))
