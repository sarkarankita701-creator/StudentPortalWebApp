from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import (
    ROLE_STUDENT,
    ROLE_SUPER_ADMIN,
    ROLE_TEACHER,
    GameAssignment,
    GamePlayResult,
    GameSession,
    User,
)
from utils.decorators import role_required
from utils.game_content import validate_game_items

games_bp = Blueprint("games", __name__, url_prefix="/games")


def _get_owned_game(game_id):
    game = GameSession.query.get_or_404(game_id)
    if current_user.is_teacher() and game.teacher_id != current_user.id:
        abort(403)
    return game


def _manage_context(game):
    students = User.query.filter_by(role=ROLE_STUDENT, is_active_flag=True).order_by(User.name).all()
    assigned_ids = {a.student_id for a in game.assignments}
    return {"game": game, "students": students, "assigned_ids": assigned_ids}


@games_bp.route("/")
@login_required
def list_games():
    if current_user.is_super_admin():
        games = GameSession.query.order_by(GameSession.created_at.desc()).all()
        return render_template("games/list.html", games=games)

    if current_user.is_teacher():
        games = GameSession.query.filter_by(teacher_id=current_user.id).order_by(GameSession.created_at.desc()).all()
        return render_template("games/list.html", games=games)

    assignments = (
        GameAssignment.query.join(GameSession)
        .filter(GameAssignment.student_id == current_user.id, GameSession.is_published.is_(True))
        .order_by(GameAssignment.assigned_at.desc())
        .all()
    )
    results = {r.game_id: r for r in GamePlayResult.query.filter_by(student_id=current_user.id).all()}
    rows = [{"game": a.game, "result": results.get(a.game_id)} for a in assignments]
    return render_template("games/student_list.html", rows=rows)


@games_bp.route("/new", methods=["GET", "POST"])
@login_required
@role_required(ROLE_TEACHER, ROLE_SUPER_ADMIN)
def new_game():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        topic = request.form.get("topic", "").strip()
        description = request.form.get("description", "").strip()

        if not title:
            flash("Title is required.", "error")
            return render_template("games/form.html")

        game = GameSession(title=title, topic=topic, description=description, teacher_id=current_user.id)
        db.session.add(game)
        db.session.commit()
        flash("Game session created. Now add items and assign students.", "success")
        return redirect(url_for("games.manage_game", game_id=game.id))

    return render_template("games/form.html")


@games_bp.route("/<int:game_id>")
@login_required
@role_required(ROLE_TEACHER, ROLE_SUPER_ADMIN)
def manage_game(game_id):
    game = _get_owned_game(game_id)
    return render_template("games/manage.html", **_manage_context(game), items_json=game.content_json or "")


@games_bp.route("/<int:game_id>/settings", methods=["POST"])
@login_required
@role_required(ROLE_TEACHER, ROLE_SUPER_ADMIN)
def update_settings(game_id):
    game = _get_owned_game(game_id)
    title = request.form.get("title", "").strip()
    topic = request.form.get("topic", "").strip()
    description = request.form.get("description", "").strip()

    if not title:
        flash("Title is required.", "error")
        return redirect(url_for("games.manage_game", game_id=game.id))

    game.title = title
    game.topic = topic
    game.description = description
    db.session.commit()
    flash("Game settings updated.", "success")
    return redirect(url_for("games.manage_game", game_id=game.id))


@games_bp.route("/<int:game_id>/items", methods=["POST"])
@login_required
@role_required(ROLE_TEACHER, ROLE_SUPER_ADMIN)
def save_items(game_id):
    game = _get_owned_game(game_id)
    raw_json = request.form.get("items_json", "").strip()

    if not raw_json:
        flash("Paste a JSON array of items first.", "error")
        return render_template("games/manage.html", **_manage_context(game), items_json=raw_json)

    try:
        validate_game_items(raw_json)
    except ValueError as exc:
        flash(str(exc), "error")
        return render_template("games/manage.html", **_manage_context(game), items_json=raw_json)

    game.content_json = raw_json
    db.session.commit()
    flash("Items saved.", "success")
    return redirect(url_for("games.manage_game", game_id=game.id))


@games_bp.route("/<int:game_id>/assign", methods=["POST"])
@login_required
@role_required(ROLE_TEACHER, ROLE_SUPER_ADMIN)
def assign_game(game_id):
    game = _get_owned_game(game_id)
    student_ids = set(int(i) for i in request.form.getlist("student_ids"))
    existing_ids = {a.student_id for a in game.assignments}

    for sid in student_ids - existing_ids:
        db.session.add(GameAssignment(game_id=game.id, student_id=sid))

    for a in list(game.assignments):
        if a.student_id not in student_ids:
            db.session.delete(a)

    db.session.commit()
    flash("Assignments updated.", "success")
    return redirect(url_for("games.manage_game", game_id=game.id))


@games_bp.route("/<int:game_id>/publish", methods=["POST"])
@login_required
@role_required(ROLE_TEACHER, ROLE_SUPER_ADMIN)
def publish_game(game_id):
    game = _get_owned_game(game_id)
    if not game.item_count:
        flash("Add at least one item before publishing.", "error")
        return redirect(url_for("games.manage_game", game_id=game.id))
    game.is_published = not game.is_published
    db.session.commit()
    flash(f"Game {'published' if game.is_published else 'unpublished'}.", "success")
    return redirect(url_for("games.manage_game", game_id=game.id))


@games_bp.route("/<int:game_id>/delete", methods=["POST"])
@login_required
@role_required(ROLE_TEACHER, ROLE_SUPER_ADMIN)
def delete_game(game_id):
    game = _get_owned_game(game_id)
    db.session.delete(game)
    db.session.commit()
    flash("Game session deleted.", "success")
    return redirect(url_for("games.list_games"))


def _get_assignment_or_403(game):
    assignment = GameAssignment.query.filter_by(game_id=game.id, student_id=current_user.id).first()
    if not assignment or not game.is_published:
        abort(403)
    return assignment


@games_bp.route("/<int:game_id>/play")
@login_required
@role_required(ROLE_STUDENT)
def play_game(game_id):
    game = GameSession.query.get_or_404(game_id)
    _get_assignment_or_403(game)

    try:
        items = validate_game_items(game.content_json or "")
    except ValueError:
        items = []

    result = GamePlayResult.query.filter_by(game_id=game.id, student_id=current_user.id).first()
    return render_template("games/play.html", game=game, items=items, result=result)


@games_bp.route("/<int:game_id>/complete", methods=["POST"])
@login_required
@role_required(ROLE_STUDENT)
def complete_game(game_id):
    game = GameSession.query.get_or_404(game_id)
    _get_assignment_or_403(game)

    total_items = request.form.get("total_items", type=int) or 0
    score = request.form.get("score", type=int) or 0
    score = max(0, min(score, total_items)) if total_items > 0 else 0

    result = GamePlayResult.query.filter_by(game_id=game.id, student_id=current_user.id).first()
    if not result:
        result = GamePlayResult(game_id=game.id, student_id=current_user.id, best_score=0, total_items=0)
        db.session.add(result)

    result.play_count = (result.play_count or 0) + 1
    result.last_played_at = datetime.utcnow()
    if score > result.best_score or not result.total_items:
        result.best_score = score
        result.total_items = total_items

    db.session.commit()
    flash(f"Score recorded: {score}/{total_items}.", "success")
    return redirect(url_for("games.play_game", game_id=game.id))
