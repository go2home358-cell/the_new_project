from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Question


def _correct_option_id(db: Session, question_id: int) -> int:
    question = db.get(Question, question_id)
    assert question is not None and question.correct_option is not None
    return question.correct_option.id


def _wrong_option_id(db: Session, question_id: int) -> int:
    question = db.get(Question, question_id)
    return next(option.id for option in question.options if not option.is_correct)


def _answer(client: TestClient, headers, attempt_id: int, question_id: int, option_id: int) -> dict:
    response = client.post(
        f"/api/v1/attempts/{attempt_id}/answers",
        json={"question_id": question_id, "selected_option_id": option_id, "time_spent_seconds": 7},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _start_practice(client: TestClient, headers, **payload) -> dict:
    response = client.post("/api/v1/practice/sessions", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_practice_session_hides_answers_until_submitted(
    client: TestClient, db: Session, seeded: dict[str, object], student_headers
) -> None:
    attempt = _start_practice(client, student_headers, mode="random", count=4)
    assert attempt["total"] == 4
    assert "is_correct" not in str(attempt["questions"])


def test_practice_answer_feedback_reveals_result_immediately(
    client: TestClient, db: Session, seeded: dict[str, object], student_headers
) -> None:
    attempt = _start_practice(client, student_headers, mode="random", count=4)
    question = attempt["questions"][0]

    right = _correct_option_id(db, question["id"])
    feedback = _answer(client, student_headers, attempt["id"], question["id"], right)
    assert feedback["is_correct"] is True
    assert feedback["correct_option_id"] == right
    assert feedback["explanation"]

    wrong = _wrong_option_id(db, question["id"])
    feedback = _answer(client, student_headers, attempt["id"], question["id"], wrong)
    assert feedback["is_correct"] is False
    assert feedback["correct_option_id"] == right


def test_scoring_and_progress_after_submission(
    client: TestClient, db: Session, seeded: dict[str, object], student_headers
) -> None:
    attempt = _start_practice(client, student_headers, mode="random", count=4)
    questions: list[dict] = attempt["questions"]
    for index, question in enumerate(questions[:3]):
        option = _correct_option_id(db, question["id"]) if index < 2 else _wrong_option_id(db, question["id"])
        _answer(client, student_headers, attempt["id"], question["id"], option)

    result = client.post(f"/api/v1/attempts/{attempt['id']}/submit", headers=student_headers).json()
    assert result["total"] == 4
    assert result["attempted"] == 3
    assert result["correct"] == 2
    assert result["incorrect"] == 1
    assert result["unattempted"] == 1
    assert result["accuracy"] == 66.67
    assert result["score"] == 50.0
    assert result["xp_earned"] == 2 * 10 + 20
    assert "🏆 First Test" in result["new_badges"]
    assert result["topic_performance"]

    summary = client.get("/api/v1/progress/summary", headers=student_headers).json()
    assert summary["questions_attempted"] == 3
    assert summary["questions_correct"] == 2
    assert summary["accuracy"] == 66.67
    assert summary["tests_completed"] == 1
    assert summary["average_score"] == 50.0
    assert summary["streak_count"] == 1
    assert summary["xp"] >= 40


def test_answers_rejected_after_submission(
    client: TestClient, db: Session, seeded: dict[str, object], student_headers
) -> None:
    attempt = _start_practice(client, student_headers, mode="random", count=4)
    question = attempt["questions"][0]
    client.post(f"/api/v1/attempts/{attempt['id']}/submit", headers=student_headers)
    response = client.post(
        f"/api/v1/attempts/{attempt['id']}/answers",
        json={"question_id": question["id"], "selected_option_id": _correct_option_id(db, question["id"])},
        headers=student_headers,
    )
    assert response.status_code == 409


def test_option_from_another_question_is_rejected(
    client: TestClient, db: Session, seeded: dict[str, object], student_headers
) -> None:
    attempt = _start_practice(client, student_headers, mode="random", count=4)
    first, second = attempt["questions"][0], attempt["questions"][1]
    response = client.post(
        f"/api/v1/attempts/{attempt['id']}/answers",
        json={"question_id": first["id"], "selected_option_id": _correct_option_id(db, second["id"])},
        headers=student_headers,
    )
    assert response.status_code == 400


def test_result_and_review_require_submission(
    client: TestClient, db: Session, seeded: dict[str, object], student_headers
) -> None:
    attempt = _start_practice(client, student_headers, mode="random", count=4)
    assert client.get(f"/api/v1/attempts/{attempt['id']}/result", headers=student_headers).status_code == 409
    assert client.get(f"/api/v1/attempts/{attempt['id']}/review", headers=student_headers).status_code == 409

    client.post(f"/api/v1/attempts/{attempt['id']}/submit", headers=student_headers)
    review = client.get(f"/api/v1/attempts/{attempt['id']}/review", headers=student_headers).json()
    assert len(review) == 4
    assert all(item["correct_option_id"] for item in review)
    assert all(item["explanation"] for item in review)


def test_attempt_of_another_user_is_not_accessible(
    client: TestClient, db: Session, seeded: dict[str, object], student_headers
) -> None:
    attempt = _start_practice(client, student_headers, mode="random", count=4)
    other = client.post(
        "/api/v1/auth/register",
        json={"name": "Other", "email": "other@example.com", "password": "OtherPass1!"},
    ).json()
    headers = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get(f"/api/v1/attempts/{attempt['id']}", headers=headers).status_code == 404


def test_timed_test_withholds_feedback_and_reports_timer(
    client: TestClient, db: Session, seeded: dict[str, object], student_headers
) -> None:
    test_id = seeded["test"].id
    attempt = client.post(f"/api/v1/tests/{test_id}/start", headers=student_headers).json()
    assert attempt["duration_seconds"] == 600
    assert attempt["title"] == "Timed Mock"

    question = attempt["questions"][0]
    feedback = _answer(client, student_headers, attempt["id"], question["id"], _correct_option_id(db, question["id"]))
    assert feedback["is_correct"] is None
    assert feedback["correct_option_id"] is None
    assert feedback["explanation"] == ""

    result = client.post(f"/api/v1/attempts/{attempt['id']}/submit", headers=student_headers).json()
    assert result["correct"] == 1
    assert result["duration_seconds"] == 600
    assert result["time_used_seconds"] <= 600


def test_wrong_question_and_bookmark_practice_modes(
    client: TestClient, db: Session, seeded: dict[str, object], student_headers
) -> None:
    attempt = _start_practice(client, student_headers, mode="random", count=4)
    wrong_ids = []
    for question in attempt["questions"][:2]:
        _answer(client, student_headers, attempt["id"], question["id"], _wrong_option_id(db, question["id"]))
        wrong_ids.append(question["id"])
    client.post(f"/api/v1/attempts/{attempt['id']}/submit", headers=student_headers)

    wrong_session = _start_practice(client, student_headers, mode="wrong", count=10)
    assert sorted(q["id"] for q in wrong_session["questions"]) == sorted(wrong_ids)

    bookmark_target = attempt["questions"][3]["id"]
    client.post(
        "/api/v1/bookmarks",
        json={"target_type": "question", "target_id": bookmark_target},
        headers=student_headers,
    )
    bookmark_session = _start_practice(client, student_headers, mode="bookmark", count=10)
    assert [q["id"] for q in bookmark_session["questions"]] == [bookmark_target]


def test_weak_topic_practice_and_analytics(
    client: TestClient, db: Session, seeded: dict[str, object], student_headers
) -> None:
    topic_id = seeded["topics"][0].id
    # A topic only counts as weak once it has enough attempts (min_attempts=3).
    for _ in range(2):
        attempt = _start_practice(client, student_headers, mode="topic", topic_id=topic_id, count=2)
        for question in attempt["questions"]:
            _answer(client, student_headers, attempt["id"], question["id"], _wrong_option_id(db, question["id"]))
        client.post(f"/api/v1/attempts/{attempt['id']}/submit", headers=student_headers)

    weak = client.get("/api/v1/progress/weak-topics", headers=student_headers).json()
    assert weak and weak[0]["topic_name"] == "Speed"
    assert weak[0]["accuracy"] == 0.0

    weak_session = _start_practice(client, student_headers, mode="weak", count=5)
    assert weak_session["total"] >= 1

    subjects = client.get("/api/v1/progress/subjects", headers=student_headers).json()
    assert subjects[0]["attempted"] == 4
    chapters = client.get(
        f"/api/v1/progress/chapters?subject_id={seeded['subject'].id}", headers=student_headers
    ).json()
    assert chapters[0]["attempted"] == 4

    history = client.get("/api/v1/attempts", headers=student_headers).json()
    assert len(history) == 2


def test_empty_selection_returns_404(client: TestClient, seeded: dict[str, object], student_headers) -> None:
    response = client.post("/api/v1/practice/sessions", json={"mode": "wrong", "count": 5}, headers=student_headers)
    assert response.status_code == 404


def test_dashboard_reports_continue_learning(
    client: TestClient, db: Session, seeded: dict[str, object], student_headers
) -> None:
    attempt = _start_practice(client, student_headers, mode="random", count=4)
    question = attempt["questions"][0]
    _answer(client, student_headers, attempt["id"], question["id"], _correct_option_id(db, question["id"]))
    client.post(f"/api/v1/attempts/{attempt['id']}/submit", headers=student_headers)

    dashboard = client.get("/api/v1/dashboard", headers=student_headers).json()
    assert dashboard["user_name"] == "Student"
    assert dashboard["summary"]["questions_attempted"] == 1
    assert dashboard["continue_learning"]["chapter_name"] == "Motion"
    assert dashboard["subjects"][0]["name"] == "Physics"


def test_study_session_and_badges(client: TestClient, seeded: dict[str, object], student_headers) -> None:
    summary = client.post(
        "/api/v1/study-sessions", json={"subject_id": seeded["subject"].id, "seconds": 300}, headers=student_headers
    ).json()
    assert summary["study_seconds"] == 300

    badges = client.get("/api/v1/badges", headers=student_headers).json()
    assert len(badges) == 5
    assert all(badge["earned"] is False for badge in badges)
