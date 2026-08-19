from fastapi.testclient import TestClient


def _question_payload(seeded: dict[str, object], text: str = "What is inertia exactly?") -> dict:
    return {
        "subject_id": seeded["subject"].id,
        "chapter_id": seeded["chapter"].id,
        "topic_id": seeded["topics"][0].id,
        "text": text,
        "explanation": "Inertia is resistance to a change in motion.",
        "difficulty": "medium",
        "source": "Admin test",
        "options": [
            {"label": "A", "text": "Mass", "is_correct": False},
            {"label": "B", "text": "Resistance to change in motion", "is_correct": True},
            {"label": "C", "text": "Force", "is_correct": False},
            {"label": "D", "text": "Momentum", "is_correct": False},
        ],
    }


def test_admin_api_rejects_students(client: TestClient, seeded: dict[str, object], student_headers) -> None:
    assert client.get("/api/v1/admin/questions", headers=student_headers).status_code == 403
    assert (
        client.post("/api/v1/admin/questions", json=_question_payload(seeded), headers=student_headers).status_code
        == 403
    )


def test_admin_api_rejects_anonymous(client: TestClient, seeded: dict[str, object]) -> None:
    assert client.get("/api/v1/admin/questions").status_code == 401


def test_admin_question_crud(client: TestClient, seeded: dict[str, object], admin_headers) -> None:
    created = client.post("/api/v1/admin/questions", json=_question_payload(seeded), headers=admin_headers)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["correct_option_id"]
    assert body["explanation"]

    payload = _question_payload(seeded, text="What is inertia, restated?")
    payload["difficulty"] = "hard"
    updated = client.put(f"/api/v1/admin/questions/{body['id']}", json=payload, headers=admin_headers)
    assert updated.status_code == 200
    assert updated.json()["difficulty"] == "hard"
    assert updated.json()["text"] == "What is inertia, restated?"

    assert client.delete(f"/api/v1/admin/questions/{body['id']}", headers=admin_headers).status_code == 204
    assert client.delete(f"/api/v1/admin/questions/{body['id']}", headers=admin_headers).status_code == 404


def test_admin_question_requires_exactly_one_correct_option(
    client: TestClient, seeded: dict[str, object], admin_headers
) -> None:
    payload = _question_payload(seeded)
    for option in payload["options"]:
        option["is_correct"] = False
    assert client.post("/api/v1/admin/questions", json=payload, headers=admin_headers).status_code == 400

    payload["options"][0]["is_correct"] = True
    payload["options"][1]["is_correct"] = True
    assert client.post("/api/v1/admin/questions", json=payload, headers=admin_headers).status_code == 400


def test_admin_question_validates_content_references(
    client: TestClient, seeded: dict[str, object], admin_headers
) -> None:
    payload = _question_payload(seeded)
    payload["chapter_id"] = 9999
    assert client.post("/api/v1/admin/questions", json=payload, headers=admin_headers).status_code == 404

    mismatched = _question_payload(seeded)
    mismatched["topic_id"] = 9999
    assert client.post("/api/v1/admin/questions", json=mismatched, headers=admin_headers).status_code == 400


def test_admin_content_creation(client: TestClient, seeded: dict[str, object], admin_headers) -> None:
    subject = client.post(
        "/api/v1/admin/subjects", json={"name": "Chemistry", "slug": "chemistry"}, headers=admin_headers
    )
    assert subject.status_code == 201
    chapter = client.post(
        "/api/v1/admin/chapters",
        json={"subject_id": subject.json()["id"], "name": "Atoms", "slug": "atoms"},
        headers=admin_headers,
    )
    assert chapter.status_code == 201
    topic = client.post(
        "/api/v1/admin/topics",
        json={"chapter_id": chapter.json()["id"], "name": "Isotopes", "slug": "isotopes"},
        headers=admin_headers,
    )
    assert topic.status_code == 201
    concept = client.post(
        "/api/v1/admin/concepts",
        json={
            "chapter_id": chapter.json()["id"],
            "kind": "concept",
            "title": "Atomic number",
            "body": "Number of protons in the nucleus.",
        },
        headers=admin_headers,
    )
    assert concept.status_code == 201


def test_admin_can_create_test_from_question_bank(client: TestClient, seeded: dict[str, object], admin_headers) -> None:
    response = client.post(
        "/api/v1/admin/tests",
        json={"title": "Admin Mock", "kind": "mock", "duration_seconds": 300, "total_questions": 3},
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["total_questions"] == 3


def test_admin_stats_and_users(client: TestClient, seeded: dict[str, object], admin_headers) -> None:
    overview = client.get("/api/v1/admin/stats/overview", headers=admin_headers).json()
    assert overview["subjects"] == 1
    assert overview["questions"] == 4

    users = client.get("/api/v1/admin/users", headers=admin_headers).json()
    assert any(user["role"] == "admin" for user in users)

    stats = client.get("/api/v1/admin/stats/questions", headers=admin_headers).json()
    assert len(stats) == 4


def test_admin_web_panel_requires_login(client: TestClient, seeded: dict[str, object]) -> None:
    assert client.get("/admin/login").status_code == 200
    redirected = client.get("/admin", follow_redirects=False)
    assert redirected.status_code == 303
    assert redirected.headers["location"] == "/admin/login"


def test_admin_web_panel_login_and_pages(client: TestClient, seeded: dict[str, object]) -> None:
    from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD

    login = client.post(
        "/admin/login",
        data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        follow_redirects=False,
    )
    assert login.status_code == 303
    for path in (
        "/admin",
        "/admin/questions",
        "/admin/questions/new",
        "/admin/content",
        "/admin/tests",
        "/admin/users",
    ):
        page = client.get(path)
        assert page.status_code == 200, path
        assert "Science Study" in page.text


def test_admin_web_panel_rejects_student_credentials(client: TestClient, seeded: dict[str, object]) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"name": "Student", "email": "webstudent@example.com", "password": "StudentPass1!"},
    )
    response = client.post(
        "/admin/login",
        data={"email": "webstudent@example.com", "password": "StudentPass1!"},
        follow_redirects=False,
    )
    assert response.status_code == 401
    assert "Invalid admin credentials" in response.text
    assert client.get("/admin", follow_redirects=False).status_code == 303
