from datetime import date, datetime

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import ROLE_STUDENT, ROLE_SUPER_ADMIN, ROLE_TEACHER, PaymentRecord, Setting, User
from utils.decorators import role_required

payments_bp = Blueprint("payments", __name__, url_prefix="/payments")


@payments_bp.route("/")
@login_required
def view():
    if current_user.is_student():
        records = (
            PaymentRecord.query.filter_by(student_id=current_user.id)
            .order_by(PaymentRecord.invoice_date.desc())
            .all()
        )
        summary = {
            "total_sessions": len(records),
            "total_due": sum(r.amount for r in records if r.status in ("pending", "awaiting_verification")),
            "total_paid": sum(r.amount for r in records if r.status == "paid"),
        }
        return render_template("payments/student_view.html", records=records, summary=summary)

    students = User.query.filter_by(role=ROLE_STUDENT).order_by(User.name).all()
    selected_id = request.args.get("student_id", type=int)
    selected_student = next((s for s in students if s.id == selected_id), None) if selected_id else None
    records = []
    if selected_student:
        records = (
            PaymentRecord.query.filter_by(student_id=selected_student.id)
            .order_by(PaymentRecord.invoice_date.desc())
            .all()
        )

    default_price = Setting.get("default_price_per_session", str(current_app.config["DEFAULT_PRICE_PER_SESSION"]))
    return render_template(
        "payments/manage.html",
        students=students,
        selected_student=selected_student,
        records=records,
        default_price=default_price,
    )


@payments_bp.route("/new", methods=["POST"])
@login_required
@role_required(ROLE_TEACHER, ROLE_SUPER_ADMIN)
def new_record():
    student_id = request.form.get("student_id", type=int)
    session_label = request.form.get("session_label", "").strip()
    invoice_date_raw = request.form.get("invoice_date")
    price = request.form.get("price_per_session", type=float)
    discount = request.form.get("discount", type=float) or 0.0
    status = request.form.get("status", "pending")
    notes = request.form.get("notes", "").strip()

    if not student_id or not session_label or not invoice_date_raw or price is None:
        flash("Student, session label, invoice date, and price are required.", "error")
        return redirect(url_for("payments.view", student_id=student_id))

    try:
        invoice_date = datetime.strptime(invoice_date_raw, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid date.", "error")
        return redirect(url_for("payments.view", student_id=student_id))

    record = PaymentRecord(
        student_id=student_id,
        session_label=session_label,
        invoice_date=invoice_date,
        price_per_session=price,
        discount=discount,
        status=status if status in ("paid", "pending") else "pending",
        notes=notes,
        recorded_by=current_user.id,
    )
    db.session.add(record)
    db.session.commit()
    flash("Payment record added.", "success")
    return redirect(url_for("payments.view", student_id=student_id))


@payments_bp.route("/<int:record_id>/claim", methods=["POST"])
@login_required
@role_required(ROLE_STUDENT)
def claim_payment(record_id):
    record = PaymentRecord.query.get_or_404(record_id)
    if record.student_id != current_user.id:
        abort(403)
    if record.status != "pending":
        flash("This record isn't awaiting a payment claim.", "error")
        return redirect(url_for("payments.view"))

    record.status = "awaiting_verification"
    db.session.commit()
    flash("Marked as paid — awaiting confirmation from your teacher/admin.", "success")
    return redirect(url_for("payments.view"))


@payments_bp.route("/<int:record_id>/confirm", methods=["POST"])
@login_required
@role_required(ROLE_TEACHER, ROLE_SUPER_ADMIN)
def confirm_payment(record_id):
    record = PaymentRecord.query.get_or_404(record_id)
    record.status = "paid"
    db.session.commit()
    flash("Payment confirmed as received.", "success")
    return redirect(url_for("payments.view", student_id=record.student_id))


@payments_bp.route("/<int:record_id>/reset", methods=["POST"])
@login_required
@role_required(ROLE_TEACHER, ROLE_SUPER_ADMIN)
def reset_payment(record_id):
    record = PaymentRecord.query.get_or_404(record_id)
    record.status = "pending"
    db.session.commit()
    flash("Payment reset to pending.", "success")
    return redirect(url_for("payments.view", student_id=record.student_id))


@payments_bp.route("/<int:record_id>/delete", methods=["POST"])
@login_required
@role_required(ROLE_TEACHER, ROLE_SUPER_ADMIN)
def delete_record(record_id):
    record = PaymentRecord.query.get_or_404(record_id)
    student_id = record.student_id
    db.session.delete(record)
    db.session.commit()
    flash("Payment record removed.", "success")
    return redirect(url_for("payments.view", student_id=student_id))
