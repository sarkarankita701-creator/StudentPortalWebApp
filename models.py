import json
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db

ROLE_SUPER_ADMIN = "super_admin"
ROLE_TEACHER = "teacher"
ROLE_STUDENT = "student"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    is_active_flag = db.Column(db.Boolean, default=True, nullable=False)
    default_meet_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return self.is_active_flag

    def is_super_admin(self):
        return self.role == ROLE_SUPER_ADMIN

    def is_teacher(self):
        return self.role == ROLE_TEACHER

    def is_student(self):
        return self.role == ROLE_STUDENT


event_assignments = db.Table(
    "event_assignments",
    db.Column("event_id", db.Integer, db.ForeignKey("calendar_events.id"), primary_key=True),
    db.Column("student_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
)

material_assignments = db.Table(
    "material_assignments",
    db.Column("material_id", db.Integer, db.ForeignKey("materials.id"), primary_key=True),
    db.Column("student_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
)


class CalendarEvent(db.Model):
    __tablename__ = "calendar_events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(120))
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    meet_url = db.Column(db.String(500))
    start_dt = db.Column(db.DateTime, nullable=False)
    end_dt = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    teacher = db.relationship("User", foreign_keys=[teacher_id])
    students = db.relationship("User", secondary=event_assignments, backref="assigned_events")


class Material(db.Model):
    __tablename__ = "materials"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(30), nullable=False)  # notes / worksheet / qa_previous_years
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content_type = db.Column(db.String(10), nullable=False, default="link")  # link / json / html
    gdrive_url = db.Column(db.String(500))
    content_json = db.Column(db.Text)
    content_html = db.Column(db.Text)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    teacher = db.relationship("User", foreign_keys=[teacher_id])
    students = db.relationship("User", secondary=material_assignments, backref="assigned_materials")


class Test(db.Model):
    __tablename__ = "tests"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False, default=30)
    rules = db.Column(db.Text)
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    teacher = db.relationship("User", foreign_keys=[teacher_id])
    questions = db.relationship("Question", backref="test", cascade="all, delete-orphan")
    assignments = db.relationship("TestAssignment", backref="test", cascade="all, delete-orphan")

    @property
    def total_marks(self):
        return sum(q.marks for q in self.questions)


class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey("tests.id"), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(500), nullable=False)
    option_b = db.Column(db.String(500), nullable=False)
    option_c = db.Column(db.String(500), nullable=False)
    option_d = db.Column(db.String(500), nullable=False)
    correct_option = db.Column(db.String(1), nullable=False)  # 'a' / 'b' / 'c' / 'd'
    marks = db.Column(db.Integer, nullable=False, default=1)


class TestAssignment(db.Model):
    __tablename__ = "test_assignments"

    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey("tests.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship("User", foreign_keys=[student_id])

    __table_args__ = (db.UniqueConstraint("test_id", "student_id", name="uq_test_student"),)


class TestAttempt(db.Model):
    __tablename__ = "test_attempts"

    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey("tests.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    submitted_at = db.Column(db.DateTime)
    score = db.Column(db.Integer)
    status = db.Column(db.String(20), default="in_progress")  # in_progress / completed

    test = db.relationship("Test", foreign_keys=[test_id])
    student = db.relationship("User", foreign_keys=[student_id])
    answers = db.relationship("AttemptAnswer", backref="attempt", cascade="all, delete-orphan")


class AttemptAnswer(db.Model):
    __tablename__ = "attempt_answers"

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey("test_attempts.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    selected_option = db.Column(db.String(1))
    is_correct = db.Column(db.Boolean, default=False)

    question = db.relationship("Question", foreign_keys=[question_id])


class GameSession(db.Model):
    __tablename__ = "game_sessions"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    topic = db.Column(db.String(120))
    description = db.Column(db.Text)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content_json = db.Column(db.Text)
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    teacher = db.relationship("User", foreign_keys=[teacher_id])
    assignments = db.relationship("GameAssignment", backref="game", cascade="all, delete-orphan")
    results = db.relationship("GamePlayResult", backref="game", cascade="all, delete-orphan")

    @property
    def item_count(self):
        if not self.content_json:
            return 0
        try:
            data = json.loads(self.content_json)
        except ValueError:
            return 0
        items = data.get("items") if isinstance(data, dict) else None
        return len(items) if isinstance(items, list) else 0


class GameAssignment(db.Model):
    __tablename__ = "game_assignments"

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("game_sessions.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship("User", foreign_keys=[student_id])

    __table_args__ = (db.UniqueConstraint("game_id", "student_id", name="uq_game_student"),)


class GamePlayResult(db.Model):
    __tablename__ = "game_play_results"

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("game_sessions.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    best_score = db.Column(db.Integer, default=0)
    total_items = db.Column(db.Integer, default=0)
    play_count = db.Column(db.Integer, default=0)
    last_played_at = db.Column(db.DateTime)

    student = db.relationship("User", foreign_keys=[student_id])

    __table_args__ = (db.UniqueConstraint("game_id", "student_id", name="uq_gameresult_student"),)


class Setting(db.Model):
    __tablename__ = "settings"

    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.String(500))

    @staticmethod
    def get(key, default=None):
        row = Setting.query.get(key)
        return row.value if row else default

    @staticmethod
    def set(key, value):
        row = Setting.query.get(key)
        if row:
            row.value = value
        else:
            row = Setting(key=key, value=value)
            db.session.add(row)
        db.session.commit()


class PaymentRecord(db.Model):
    __tablename__ = "payment_records"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    session_label = db.Column(db.String(200), nullable=False)
    invoice_date = db.Column(db.Date, nullable=False)
    price_per_session = db.Column(db.Float, nullable=False, default=0.0)
    discount = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(20), default="pending")  # pending / awaiting_verification / paid
    notes = db.Column(db.Text)
    recorded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship("User", foreign_keys=[student_id])

    @property
    def amount(self):
        return max(self.price_per_session - self.discount, 0.0)


class DoubtSessionRequest(db.Model):
    __tablename__ = "doubt_session_requests"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    topic = db.Column(db.Text, nullable=False)
    proposed_dt = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False, default=30)
    status = db.Column(db.String(20), default="pending")  # pending / approved / rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    calendar_event_id = db.Column(db.Integer, db.ForeignKey("calendar_events.id"))

    student = db.relationship("User", foreign_keys=[student_id])
    teacher = db.relationship("User", foreign_keys=[teacher_id])
    calendar_event = db.relationship("CalendarEvent", foreign_keys=[calendar_event_id])
