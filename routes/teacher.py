from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import ROLE_TEACHER
from utils.decorators import role_required

teacher_bp = Blueprint("teacher", __name__, url_prefix="/teacher")


@teacher_bp.route("/settings", methods=["GET", "POST"])
@login_required
@role_required(ROLE_TEACHER)
def settings():
    if request.method == "POST":
        current_user.default_meet_url = request.form.get("default_meet_url", "").strip()
        db.session.commit()
        flash("Settings updated.", "success")
        return redirect(url_for("teacher.settings"))

    return render_template("teacher/settings.html")
