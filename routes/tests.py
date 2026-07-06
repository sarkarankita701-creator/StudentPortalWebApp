from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import (
    ROLE_STUDENT,
    ROLE_SUPER_ADMIN,
    ROLE_TEACHER,
    AttemptAnswer,
    Question,
    Test,
    TestAssignment,
    TestAttempt,
    User,
)
from utils.decorators import role_required

tests_bp = Blueprint("tests", __name__, url_prefix="/tests")


def _latest_attempt(test_id, student_id):
    return (
        TestAttempt.query.filter_by(test_id=test_id, student_id=student_id)
        .order_by(TestAttempt.started_at.desc())
        .first()
    )


@tests_bp.route("/")
@login_required
def list_tests():
    if current_user.is_super_admin():
        tests = Test.query.order_by(Test.created_at.desc()).all()
        return render_template("tests/list.html", tests=tests)

    if current_user.is_teacher():
        tests = Test.query.filter_by(teacher_id=current_user.id).order_by(Test.created_at.desc()).all()
        return render_template("tests/list.html", tests=tests)

    assignments = (
        TestAssignment.query.join(Test)
        .filter(TestAssignment.student_id == current_user.id, Test.is_published.is_(True))
        .order_by(TestAssignment.assigned_at.desc())
        .all()
    )
    rows = []
    for a in assignments:
        attempt = _latest_attempt(a.test_id, current_user.id)
        rows.append({"test": a.test, "attempt": attempt})
    return render_template("tests/student_list.html", rows=rows)


@tests_bp.route("/new", methods=["GET", "POST"])
@login_required
@role_required(ROLE_TEACHER, ROLE_SUPER_ADMIN)
def new_test():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        duration = request.form.get("duration_minutes", type=int)
        rules = request.form.get("rules", "").strip()

        if not title or not duration or duration <= 0:
            flash("Title and a positive duration (minutes) are required.", "error")
            return render_template("tests/form.html")

        test = Test(title=title, teacher_id=current_user.id, duration_minutes=duration, rules=rules)
        db.session.add(test)
        db.session.commit()
        flash("Test created. Now add questions and assign students.", "success")
        return redirect(url_for("tests.manage_test", test_id=test.id))

    return render_template("tests/form.html")


def _get_owned_test(test_id):
    test = Test.query.get_or_404(test_id)
    if current_user.is_teacher() and test.teacher_id != current_user.id:
        abort(403)
    return test


@tests_bp.route("/<int:test_id>")
@login_required
@role_required(ROLE_TEACHER, ROLE_SUPER_ADMIN)
def manage_test(test_id):
    test = _get_owned_test(test_id)
    students = User.query.filter_by(role=ROLE_STUDENT, is_active_flag=True).order_by(User.name).all()
    assigned_ids = {a.student_id for a in test.assignments}
    return render_template("tests/manage.html", test=test, students=students, assigned_ids=assigned_ids)


@tests_bp.route("/<int:test_id>/rules", methods=["POST"])
@login_required
@role_required(ROLE_TEACHER, ROLE_SUPER_ADMIN)
def update_rules(test_id):
    test = _get_owned_test(test_id)
    test.rules = request.form.get("rules", "").strip()
    db.session.commit()
    flash("Test rules updated.", "success")
    return redirect(url_for("tests.manage_test", test_id=test.id))


@tests_bp.route("/<int:test_id>/questions/new", methods=["POST"])
@login_required
@role_required(ROLE_TEACHER, ROLE_SUPER_ADMIN)
def add_question(test_id):
    test = _get_owned_test(test_id)

    question_text = request.form.get("question_text", "").strip()
    option_a = request.form.get("option_a", "").strip()
    option_b = request.form.get("option_b", "").strip()
    option_c = request.form.get("option_c", "").strip()
    option_d = request.form.get("option_d", "").strip()
    correct_option = request.form.get("correct_option")
    marks = request.form.get("marks", type=int, default=1)

    if not all([question_text, option_a, option_b, option_c, option_d]) or correct_option not in ("a", "b", "c", "d"):
        flash("All question fields and a correct option are required.", "error")
        return redirect(url_for("tests.manage_test", test_id=test.id))

    question = Question(
        test_id=test.id,
        question_text=question_text,
        option_a=option_a,
        option_b=option_b,
        option_c=option_c,
        option_d=option_d,
        correct_option=correct_option,
        marks=marks or 1,
    )
    db.session.add(question)
    db.session.commit()
    flash("Question added.", "success")
    return redirect(url_for("tests.manage_test", test_id=test.id))


@tests_bp.route("/<int:test_id>/questions/<int:question_id>/delete", methods=["POST"])
@login_required
@role_required(ROLE_TEACHER, ROLE_SUPER_ADMIN)
def delete_question(test_id, question_id):
    test = _get_owned_test(test_id)
    question = Question.query.filter_by(id=question_id, test_id=test.id).first_or_404()
    db.session.delete(question)
    db.session.commit()
    flash("Question removed.", "success")
    return redirect(url_for("tests.manage_test", test_id=test.id))


@tests_bp.route("/<int:test_id>/assign", methods=["POST"])
@login_required
@role_required(ROLE_TEACHER, ROLE_SUPER_ADMIN)
def assign_test(test_id):
    test = _get_owned_test(test_id)
    student_ids = set(int(i) for i in request.form.getlist("student_ids"))
    existing_ids = {a.student_id for a in test.assignments}

    for sid in student_ids - existing_ids:
        db.session.add(TestAssignment(test_id=test.id, student_id=sid))

    for a in list(test.assignments):
        if a.student_id not in student_ids:
            db.session.delete(a)

    db.session.commit()
    flash("Assignments updated.", "success")
    return redirect(url_for("tests.manage_test", test_id=test.id))


@tests_bp.route("/<int:test_id>/publish", methods=["POST"])
@login_required
@role_required(ROLE_TEACHER, ROLE_SUPER_ADMIN)
def publish_test(test_id):
    test = _get_owned_test(test_id)
    if not test.questions:
        flash("Add at least one question before publishing.", "error")
        return redirect(url_for("tests.manage_test", test_id=test.id))
    test.is_published = not test.is_published
    db.session.commit()
    flash(f"Test {'published' if test.is_published else 'unpublished'}.", "success")
    return redirect(url_for("tests.manage_test", test_id=test.id))


def _get_assignment_or_403(test):
    assignment = TestAssignment.query.filter_by(test_id=test.id, student_id=current_user.id).first()
    if not assignment or not test.is_published:
        abort(403)
    return assignment


@tests_bp.route("/<int:test_id>/take", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def take_test(test_id):
    test = Test.query.get_or_404(test_id)
    _get_assignment_or_403(test)

    attempt = _latest_attempt(test.id, current_user.id)
    if attempt and attempt.status == "completed":
        return redirect(url_for("tests.result", test_id=test.id))

    if attempt and attempt.status == "in_progress":
        return redirect(url_for("tests.attempt_test", test_id=test.id))

    return render_template("tests/instructions.html", test=test)


@tests_bp.route("/<int:test_id>/start", methods=["POST"])
@login_required
@role_required(ROLE_STUDENT)
def start_test(test_id):
    test = Test.query.get_or_404(test_id)
    _get_assignment_or_403(test)

    attempt = _latest_attempt(test.id, current_user.id)
    if attempt:
        if attempt.status == "completed":
            return redirect(url_for("tests.result", test_id=test.id))
        return redirect(url_for("tests.attempt_test", test_id=test.id))

    attempt = TestAttempt(test_id=test.id, student_id=current_user.id, started_at=datetime.utcnow())
    db.session.add(attempt)
    db.session.commit()
    return redirect(url_for("tests.attempt_test", test_id=test.id))


@tests_bp.route("/<int:test_id>/attempt", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def attempt_test(test_id):
    test = Test.query.get_or_404(test_id)
    _get_assignment_or_403(test)

    attempt = _latest_attempt(test.id, current_user.id)
    if attempt and attempt.status == "completed":
        return redirect(url_for("tests.result", test_id=test.id))
    if not attempt:
        return redirect(url_for("tests.take_test", test_id=test.id))

    elapsed_seconds = (datetime.utcnow() - attempt.started_at).total_seconds()
    remaining_seconds = max(test.duration_minutes * 60 - int(elapsed_seconds), 0)

    return render_template("tests/take.html", test=test, attempt=attempt, remaining_seconds=remaining_seconds)


@tests_bp.route("/<int:test_id>/submit", methods=["POST"])
@login_required
@role_required(ROLE_STUDENT)
def submit_test(test_id):
    test = Test.query.get_or_404(test_id)
    attempt = _latest_attempt(test.id, current_user.id)
    if not attempt or attempt.status == "completed":
        abort(403)

    score = 0
    for question in test.questions:
        selected = request.form.get(f"question_{question.id}")
        is_correct = selected == question.correct_option
        if is_correct:
            score += question.marks
        db.session.add(
            AttemptAnswer(
                attempt_id=attempt.id,
                question_id=question.id,
                selected_option=selected,
                is_correct=is_correct,
            )
        )

    attempt.score = score
    attempt.status = "completed"
    attempt.submitted_at = datetime.utcnow()
    db.session.commit()
    flash("Test submitted.", "success")
    return redirect(url_for("tests.result", test_id=test.id))


@tests_bp.route("/<int:test_id>/result")
@login_required
def result(test_id):
    test = Test.query.get_or_404(test_id)

    if current_user.is_student():
        attempt = _latest_attempt(test.id, current_user.id)
        if not attempt or attempt.status != "completed":
            abort(404)
    else:
        student_id = request.args.get("student_id", type=int)
        if current_user.is_teacher() and test.teacher_id != current_user.id:
            abort(403)
        if not student_id:
            abort(400)
        attempt = _latest_attempt(test.id, student_id)
        if not attempt or attempt.status != "completed":
            abort(404)

    return render_template("tests/result.html", test=test, attempt=attempt)
