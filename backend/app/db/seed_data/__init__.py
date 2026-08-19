from app.db.seed_data import biology, chemistry, mathematics, physics

SUBJECTS = [physics.SUBJECT, chemistry.SUBJECT, biology.SUBJECT, mathematics.SUBJECT]

__all__ = ["SUBJECTS"]
