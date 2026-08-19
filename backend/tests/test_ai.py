from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Concept
from app.services import ai


def test_validate_generated_accepts_a_well_formed_question() -> None:
    ok, reason = ai.validate_generated(
        {
            "text": "Which quantity is measured in newtons?",
            "options": [
                {"label": "A", "text": "Force", "is_correct": True},
                {"label": "B", "text": "Energy", "is_correct": False},
                {"label": "C", "text": "Power", "is_correct": False},
                {"label": "D", "text": "Pressure", "is_correct": False},
            ],
            "explanation": "The newton is the SI unit of force.",
        }
    )
    assert ok and reason == ""


def test_validate_generated_rejects_bad_shapes() -> None:
    base = {
        "text": "Which quantity is measured in newtons?",
        "options": [
            {"label": "A", "text": "Force", "is_correct": True},
            {"label": "B", "text": "Energy", "is_correct": False},
            {"label": "C", "text": "Power", "is_correct": False},
            {"label": "D", "text": "Pressure", "is_correct": False},
        ],
        "explanation": "The newton is the SI unit of force.",
    }

    too_few = {**base, "options": base["options"][:3]}
    assert ai.validate_generated(too_few)[0] is False

    two_correct = {**base, "options": [{**o, "is_correct": True} for o in base["options"]]}
    assert ai.validate_generated(two_correct)[0] is False

    none_correct = {**base, "options": [{**o, "is_correct": False} for o in base["options"]]}
    assert ai.validate_generated(none_correct)[0] is False

    assert ai.validate_generated({**base, "explanation": "short"})[0] is False
    assert ai.validate_generated({**base, "text": "Why?"})[0] is False
    bad_labels = {**base, "options": [{**o, "label": "X"} for o in base["options"]]}
    assert ai.validate_generated(bad_labels)[0] is False


def test_ask_falls_back_to_stored_material_when_unconfigured(
    client: TestClient, db: Session, seeded: dict[str, object], student_headers
) -> None:
    db.add(
        Concept(
            chapter_id=seeded["chapter"].id,
            kind="concept",
            title="Newton's first law",
            body="A body continues in its state of rest or uniform motion unless acted upon by a force.",
        )
    )
    db.commit()

    response = client.post(
        "/api/v1/ai/ask", json={"question": "uniform motion", "language": "en"}, headers=student_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "study_material"
    assert "Newton's first law" in body["answer"]


def test_ask_admits_when_it_has_no_answer(client: TestClient, seeded: dict[str, object], student_headers) -> None:
    body = client.post(
        "/api/v1/ai/ask", json={"question": "quantum chromodynamics", "language": "en"}, headers=student_headers
    ).json()
    assert body["source"] == "unavailable"
    assert body["confident"] is False


def test_marathi_fallback_is_localised(client: TestClient, seeded: dict[str, object], student_headers) -> None:
    body = client.post(
        "/api/v1/ai/ask", json={"question": "quantum chromodynamics", "language": "mr"}, headers=student_headers
    ).json()
    assert body["language"] == "mr"
    assert "कॉन्फिगर" in body["answer"]


def test_question_generation_reports_missing_provider(
    client: TestClient, seeded: dict[str, object], admin_headers
) -> None:
    response = client.post(
        "/api/v1/ai/generate-questions",
        json={"subject_id": seeded["subject"].id, "difficulty": "medium", "count": 3},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] == []
    assert body["rejected"] == ["AI provider is not configured (set AI_API_KEY)"]


def test_question_generation_is_admin_only(client: TestClient, seeded: dict[str, object], student_headers) -> None:
    response = client.post(
        "/api/v1/ai/generate-questions",
        json={"subject_id": seeded["subject"].id, "difficulty": "medium", "count": 3},
        headers=student_headers,
    )
    assert response.status_code == 403
