from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import ROLE_STUDENT, ROLE_SUPER_ADMIN, ROLE_TEACHER, Material, User
from utils.decorators import role_required
from utils.material_content import sanitize_note_html, validate_content_blocks

materials_bp = Blueprint("materials", __name__, url_prefix="/materials")

CATEGORIES = {
    "notes": "Notes",
    "worksheet": "Worksheets",
    "qa_previous_years": "QA - Previous Years",
}

CONTENT_TYPES = {
    "link": "Google Drive Link",
    "json": "Structured Content (JSON)",
    "html": "Structured Content (HTML)",
}


@materials_bp.route("/")
@login_required
def list_materials():
    if current_user.is_super_admin() or current_user.is_teacher():
        materials = Material.query.order_by(Material.created_at.desc()).all()
    else:
        materials = sorted(current_user.assigned_materials, key=lambda m: m.created_at, reverse=True)

    grouped = {key: [] for key in CATEGORIES}
    for m in materials:
        grouped.setdefault(m.category, []).append(m)

    return render_template("materials/list.html", grouped=grouped, categories=CATEGORIES)


def _populate_from_form(material):
    """Read + validate request.form into `material`. Returns an error message, or None on success."""
    title = request.form.get("title", "").strip()
    category = request.form.get("category")
    content_type = request.form.get("content_type", "link")
    description = request.form.get("description", "").strip()
    student_ids = request.form.getlist("student_ids")

    if not title or category not in CATEGORIES or content_type not in CONTENT_TYPES:
        return "Title, category, and a content source are required."

    gdrive_url = content_json = content_html = None

    if content_type == "link":
        gdrive_url = request.form.get("gdrive_url", "").strip()
        if not gdrive_url:
            return "A Google Drive link is required."
    else:
        raw_content = request.form.get("content_input", "").strip()
        if not raw_content:
            return "Paste the JSON or HTML content, or switch back to Google Drive Link."
        if content_type == "json":
            try:
                validate_content_blocks(raw_content)
            except ValueError as exc:
                return str(exc)
            content_json = raw_content
        else:  # html
            content_html = sanitize_note_html(raw_content)
            if not content_html.strip():
                return "That HTML didn't contain any allowed content after sanitizing (e.g. only scripts/styles)."

    material.title = title
    material.category = category
    material.content_type = content_type
    material.gdrive_url = gdrive_url
    material.content_json = content_json
    material.content_html = content_html
    material.description = description
    material.students = User.query.filter(User.id.in_(student_ids)).all() if student_ids else []
    return None


@materials_bp.route("/new", methods=["GET", "POST"])
@login_required
@role_required(ROLE_TEACHER, ROLE_SUPER_ADMIN)
def new_material():
    students = User.query.filter_by(role=ROLE_STUDENT, is_active_flag=True).order_by(User.name).all()

    if request.method == "POST":
        material = Material(teacher_id=current_user.id)
        error = _populate_from_form(material)
        if error:
            flash(error, "error")
            return render_template(
                "materials/form.html", students=students, categories=CATEGORIES,
                content_types=CONTENT_TYPES, material=None, form_data=request.form,
            )

        db.session.add(material)
        db.session.commit()
        flash("Material added.", "success")
        return redirect(url_for("materials.list_materials"))

    return render_template(
        "materials/form.html", students=students, categories=CATEGORIES,
        content_types=CONTENT_TYPES, material=None, form_data=None,
    )


@materials_bp.route("/<int:material_id>/edit", methods=["GET", "POST"])
@login_required
@role_required(ROLE_TEACHER, ROLE_SUPER_ADMIN)
def edit_material(material_id):
    material = Material.query.get_or_404(material_id)
    students = User.query.filter_by(role=ROLE_STUDENT, is_active_flag=True).order_by(User.name).all()

    if request.method == "POST":
        error = _populate_from_form(material)
        if error:
            flash(error, "error")
            return render_template(
                "materials/form.html", students=students, categories=CATEGORIES,
                content_types=CONTENT_TYPES, material=material, form_data=request.form,
            )

        db.session.commit()
        flash("Material updated.", "success")
        return redirect(url_for("materials.list_materials"))

    return render_template(
        "materials/form.html", students=students, categories=CATEGORIES,
        content_types=CONTENT_TYPES, material=material, form_data=None,
    )


@materials_bp.route("/<int:material_id>/view")
@login_required
def view_material(material_id):
    material = Material.query.get_or_404(material_id)

    if current_user.is_student() and material not in current_user.assigned_materials:
        abort(403)

    if material.content_type == "link":
        return redirect(material.gdrive_url)

    if material.content_type == "json":
        try:
            blocks = validate_content_blocks(material.content_json)
        except ValueError as exc:
            flash(f"This note's content is invalid and can't be displayed: {exc}", "error")
            return redirect(url_for("materials.list_materials"))
        return render_template("materials/view.html", material=material, blocks=blocks)

    return render_template("materials/view.html", material=material, blocks=None)


@materials_bp.route("/<int:material_id>/delete", methods=["POST"])
@login_required
@role_required(ROLE_TEACHER, ROLE_SUPER_ADMIN)
def delete_material(material_id):
    material = Material.query.get_or_404(material_id)
    db.session.delete(material)
    db.session.commit()
    flash("Material removed.", "success")
    return redirect(url_for("materials.list_materials"))
