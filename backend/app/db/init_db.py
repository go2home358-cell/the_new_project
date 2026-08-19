"""Create all tables. Run with `python -m app.db.init_db`."""

from app.db.base import Base
from app.db.session import engine
from app.models import *  # noqa: F401,F403  (import models so metadata is populated)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Tables created.")
