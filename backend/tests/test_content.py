from fastapi.testclient import TestClient


def test_subjects_require_authentication(client: TestClient, seeded: dict[str, object]) -> None:
    assert client.get("/api/v1/subjects").status_code == 401


def test_subject_and_chapter_browsing(client: TestClient, seeded: dict[str, object], student_headers) -> None:
    subjects = client.get("/api/v1/subjects", headers=student_headers).json()
    assert [subject["name"] for subject in subjects] == ["Physics"]
    subject_id = subjects[0]["id"]

    chapters = client.get(f"/api/v1/subjects/{subject_id}/chapters", headers=student_headers).json()
    assert chapters[0]["name"] == "Motion"
    assert chapters[0]["question_count"] == 4

    chapter = client.get(f"/api/v1/chapters/{chapters[0]['id']}", headers=student_headers).json()
    assert [topic["name"] for topic in chapter["topics"]] == ["Speed", "Acceleration"]


def test_missing_chapter_returns_404(client: TestClient, seeded: dict[str, object], student_headers) -> None:
    assert client.get("/api/v1/chapters/9999", headers=student_headers).status_code == 404


def test_question_list_never_exposes_the_correct_answer(
    client: TestClient, seeded: dict[str, object], student_headers
) -> None:
    response = client.get("/api/v1/questions?limit=4", headers=student_headers)
    assert response.status_code == 200
    body = response.text
    assert "is_correct" not in body
    assert "explanation" not in body
    for question in response.json():
        assert len(question["options"]) == 4
        assert set(question["options"][0]) == {"id", "label", "text"}


def test_questions_filter_by_topic(client: TestClient, seeded: dict[str, object], student_headers) -> None:
    topic_id = seeded["topics"][1].id
    questions = client.get(f"/api/v1/questions?topic_id={topic_id}", headers=student_headers).json()
    assert len(questions) == 2
    assert all(question["topic_id"] == topic_id for question in questions)


def test_search_matches_chapters_topics_and_questions(
    client: TestClient, seeded: dict[str, object], student_headers
) -> None:
    results = client.get("/api/v1/search?q=motion", headers=student_headers).json()["results"]
    assert any(item["kind"] == "chapter" and item["title"] == "Motion" for item in results)


def test_bookmark_lifecycle(client: TestClient, seeded: dict[str, object], student_headers) -> None:
    question_id = seeded["questions"][0].id
    created = client.post(
        "/api/v1/bookmarks",
        json={"target_type": "question", "target_id": question_id},
        headers=student_headers,
    )
    assert created.status_code == 201
    listed = client.get("/api/v1/bookmarks", headers=student_headers).json()
    assert len(listed) == 1

    questions = client.get("/api/v1/questions", headers=student_headers).json()
    assert next(q["is_bookmarked"] for q in questions if q["id"] == question_id) is True

    assert client.delete(f"/api/v1/bookmarks/{created.json()['id']}", headers=student_headers).status_code == 204
    assert client.get("/api/v1/bookmarks", headers=student_headers).json() == []
