# Online Tuition Portal

Single-process Flask app (server-rendered HTML, SQLite) for running an online tuition business with three roles: Super Admin, Teacher, Student.

## Run it

```
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python app.py
```

Open http://127.0.0.1:5000 — the first run seeds a Super Admin account and prints its username/password to the console (default `admin` / `admin123`, override with the `SUPER_ADMIN_USERNAME` / `SUPER_ADMIN_PASSWORD` env vars). Log in as that admin and change the password by creating a new admin-managed flow, or simply update it directly for now.

## Roles

- **Super Admin**: creates Teacher/Student accounts (`Users`), manages the payment QR code image and default session price (`Settings`).
- **Teacher**: schedules calendar sessions (with a Google Meet link), adds Material Bank items (Google Drive links), and builds/publishes MCQ tests — each assigned to specific students.
- **Student**: sees only calendar events, materials, and tests assigned to them; takes timed tests; views their own performance history and payment records.

## Notes / known limitations

- Materials are Google Drive links only — no file upload/storage.
- Payments are tracked manually (no payment gateway) — a static QR code plus admin/teacher-entered session records.
- Tests are MCQ-only, one attempt per student per test (no retakes, no autosave — if the browser closes mid-test the attempt stays "in progress").

## Data persistence & deploying updates

All data lives in `instance/app.db` (SQLite), next to the code, and is **not** tracked in git (see `.gitignore`). To deploy an update:

```
git pull
venv\Scripts\pip install -r requirements.txt   # only needed if requirements.txt changed
venv\Scripts\python app.py
```

That's it — restarting the process never touches `instance/app.db`, so all existing users, calendar events, materials, tests, attempts, and payment records survive every restart and every redeploy, as long as:

- You always `git pull` **in the same directory** (never redeploy by cloning into a fresh folder) — the database file lives inside this checkout.
- You never delete `instance/app.db`.

On startup the app runs any pending [Flask-Migrate](https://flask-migrate.readthedocs.io/) migrations automatically (`migrations/` is committed to git — it's schema code, not data), so schema changes apply in place without wiping existing rows.

**If you ever change `models.py`** (add a field, a table, etc.), generate a migration for it *before* deploying:

```
venv\Scripts\flask db migrate -m "describe the change"
```

Review the generated file under `migrations/versions/`, commit it along with your model change, then deploy as usual — the next `python app.py` run applies it automatically.
