from flask import Blueprint, render_template, request
from flask_login import current_user, login_required

from models import ROLE_STUDENT, ROLE_SUPER_ADMIN, ROLE_TEACHER, Test, TestAttempt, User

performance_bp = Blueprint("performance", __name__, url_prefix="/performance")


def _attempt_rows(attempts):
    rows = []
    for a in attempts:
        total = a.test.total_marks
        pct = round((a.score / total * 100), 1) if total else 0
        rows.append({"attempt": a, "test": a.test, "pct": pct})
    return rows


@performance_bp.route("/")
@login_required
def view():
    if current_user.is_student():
        attempts = (
            TestAttempt.query.filter_by(student_id=current_user.id, status="completed")
            .order_by(TestAttempt.submitted_at.desc())
            .all()
        )
        rows = _attempt_rows(attempts)
        avg_pct = round(sum(r["pct"] for r in rows) / len(rows), 1) if rows else 0
        return render_template("performance/student_view.html", rows=rows, avg_pct=avg_pct)

    # teacher / super admin: pick a student to view
    if current_user.is_teacher():
        assigned_student_ids = {
            sid
            for t in Test.query.filter_by(teacher_id=current_user.id).all()
            for a in t.assignments
            for sid in [a.student_id]
        }
        students = User.query.filter(User.id.in_(assigned_student_ids)).order_by(User.name).all()
    else:
        students = User.query.filter_by(role=ROLE_STUDENT).order_by(User.name).all()

    selected_id = request.args.get("student_id", type=int)
    rows = []
    avg_pct = 0
    selected_student = None
    if selected_id:
        selected_student = next((s for s in students if s.id == selected_id), None)
        if selected_student:
            attempts = (
                TestAttempt.query.filter_by(student_id=selected_id, status="completed")
                .order_by(TestAttempt.submitted_at.desc())
                .all()
            )
            if current_user.is_teacher():
                attempts = [a for a in attempts if a.test.teacher_id == current_user.id]
            rows = _attempt_rows(attempts)
            avg_pct = round(sum(r["pct"] for r in rows) / len(rows), 1) if rows else 0

    return render_template(
        "performance/teacher_view.html",
        students=students,
        selected_student=selected_student,
        rows=rows,
        avg_pct=avg_pct,
    )
