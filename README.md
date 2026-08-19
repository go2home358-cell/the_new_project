# Science Study

An Android-first study app for competitive-exam science students, built around the loop
**Learn → Practice → Test → Analyze → Revise**. Physics, Chemistry, Biology and Mathematics
ship with seeded study material and MCQs; the schema is subject-agnostic so more subjects or
exams can be added without migrations to the app.

- `backend/` — FastAPI + PostgreSQL API and a server-rendered admin panel
- `mobile/` — Flutter client (Android, also builds for web)

## Features

**Learn** — subjects → chapters → topics, with concepts, formulas, solved examples and
one-line revision points per chapter. Concepts can be bookmarked.

**Practice** — MCQ sessions by topic, chapter or subject, plus random, weak-topic,
previously-wrong and bookmarked-question modes. Instant feedback with explanations.

**Test** — timed mock tests and a daily challenge, with a question palette,
mark-for-review, clear-answer and auto-expiry on the server clock.

**Analyze** — per-attempt scoring (correct / incorrect / skipped, accuracy, score, time),
topic performance, weak-topic detection, subject and chapter progress, study time, streaks,
XP, levels and badges.

**Revise** — wrong-question and bookmark drills, search across chapters/topics/questions,
and an optional AI tutor that falls back to stored study material (never invents an answer)
when no provider is configured.

**Admin** — REST endpoints and a web panel for content, questions (with exactly-one-correct
validation), tests and users, plus validated AI question generation for admins only.

## Architecture

```
Flutter (Material 3)
  ui/screens, ui/widgets      screens and shared widgets
  state/                      ChangeNotifier controllers (auth, attempt player)
  data/                       repositories, one per API area
  core/                       API client (JWT + one-shot refresh), token storage, theme
  models/                     immutable models parsing the API payloads

FastAPI
  api/v1/                     auth, content, questions, practice, progress, bookmarks, ai, admin
  services/                   practice selection, scoring, progress, gamification, ai
  models/, schemas/           SQLAlchemy 2.0 models and Pydantic 2 schemas
  admin/                      Jinja2 admin panel
  db/                         metadata bootstrap and idempotent seed data
```

Student question payloads never contain the correct option; explanations are only returned
after an answer in practice mode or after submitting a test.

## Backend setup

Requires Python 3.10+ and PostgreSQL 14+.

```bash
# database
sudo -u postgres psql -c "CREATE USER science WITH PASSWORD '<password>';"
sudo -u postgres psql -c "CREATE DATABASE science_study OWNER science;"
sudo -u postgres psql -c "CREATE DATABASE science_study_test OWNER science;"

# app
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then fill in DATABASE_URL and JWT_SECRET_KEY

python -m app.db.init_db      # create tables
python -m app.db.seed         # idempotent study material + questions + tests
uvicorn app.main:app --reload --port 8000
```

- API: `http://127.0.0.1:8000/api/v1`, docs at `/docs`, health at `/health`
- Admin panel: `http://127.0.0.1:8000/admin` (any user with `role = admin`)

The first admin is bootstrapped from `.env`: set `ADMIN_EMAIL`, `ADMIN_PASSWORD` and
optionally `ADMIN_NAME`, then run `python -m app.db.seed` again — an existing user with that
email is promoted, otherwise the account is created.

`.env` is git-ignored. `JWT_SECRET_KEY` must be set to a random value in any deployment;
`AI_PROVIDER`/`AI_API_KEY` are optional and the AI endpoints degrade gracefully without them.

## Mobile setup

Requires Flutter 3.27+ (developed on 3.47) and, for APKs, the Android SDK (platform 35).

```bash
cd mobile
flutter pub get

# Android emulator reaches the host backend on 10.0.2.2 (the default)
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1

# physical device on the same network
flutter run --dart-define=API_BASE_URL=http://<host-lan-ip>:8000/api/v1
```

Release APK:

```bash
flutter build apk --release --dart-define=API_BASE_URL=https://<your-api-host>/api/v1
# build/app/outputs/flutter-apk/app-release.apk
```

The release build is signed with the debug key until a keystore is provided in
`android/key.properties`; do that before publishing.

## Tests and checks

```bash
cd backend && pytest -q && ruff check . && ruff format --check .
cd mobile  && flutter analyze && flutter test
```

The backend suite covers auth, content payload safety, practice selection, timer expiry,
scoring, progress, bookmarks, AI validation and the admin surface. The Flutter suite covers
model parsing, the API client's refresh behaviour, auth state and the attempt player
(practice feedback, timed tests, mark-for-review).

## Roadmap

Shipped: authentication, learning content, practice, timed tests, results and review,
progress analytics, bookmarks, wrong-question drills, search, badges, admin tooling, AI
fallback and Marathi-language plumbing on the AI endpoint.

Next: push notifications, richer gamification (leaderboards), offline downloads of chapters,
Marathi translations of the seeded material, and personalised study plans.
