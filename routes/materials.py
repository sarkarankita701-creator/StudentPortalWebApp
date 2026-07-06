from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import ROLE_STUDENT, ROLE_SUPER_ADMIN, ROLE_TEACHER, Material, User
from utils.decorators import role_required

materials_bp = Blueprint("materials", __name__, url_prefix="/materials")

CATEGORIES = {
    "notes": "Notes",
    "worksheet": "Worksheets",
    "qa_previous_years": "QA - Previous Years",
}


@materials_bp.route("/")
@login_required
def list_materials():
    if current_user.is_super_admin():
        materials = Material.query.order_by(Material.created_at.desc()).all()
    elif current_user.is_teacher():
        materials = Material.query.filter_by(teacher_id=current_user.id).order_by(Material.created_at.desc()).all()
    else:
        materials = sorted(current_user.assigned_materials, key=lambda m: m.created_at, reverse=True)

    grouped = {key: [] for key in CATEGORIES}
    for m in materials:
        grouped.setdefault(m.category, []).append(m)

    return render_template("materials/list.html", grouped=grouped, categories=CATEGORIES)


@materials_bp.route("/new", methods=["GET", "POST"])
@login_required
@role_required(ROLE_TEACHER, ROLE_SUPER_ADMIN)
def new_material():
    students = User.query.filter_by(role=ROLE_STUDENT, is_active_flag=True).order_by(User.name).all()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category")
        gdrive_url = request.form.get("gdrive_url", "").strip()
        description = request.form.get("description", "").strip()
        student_ids = request.form.getlist("student_ids")

        if not title or category not in CATEGORIES or not gdrive_url:
            flash("Title, category, and a Google Drive link are required.", "error")
            return render_template("materials/form.html", students=students, categories=CATEGORIES)

        material = Material(
            title=title,
            category=category,
            teacher_id=current_user.id,
            gdrive_url=gdrive_url,
            description=description,
        )
        if student_ids:
            material.students = User.query.filter(User.id.in_(student_ids)).all()

        db.session.add(material)
        db.session.commit()
        flash("Material added.", "success")
        return redirect(url_for("materials.list_materials"))

    return render_template("materials/form.html", students=students, categories=CATEGORIES)


@materials_bp.route("/<int:material_id>/delete", methods=["POST"])
@login_required
@role_required(ROLE_TEACHER, ROLE_SUPER_ADMIN)
def delete_material(material_id):
    material = Material.query.get_or_404(material_id)
    if current_user.is_teacher() and material.teacher_id != current_user.id:
        abort(403)
    db.session.delete(material)
    db.session.commit()
    flash("Material removed.", "success")
    return redirect(url_for("materials.list_materials"))
