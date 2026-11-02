import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./vaultpay.db")
# Normalise plain Postgres URLs (e.g. Neon) to the psycopg (v3) driver
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgresql://"):]
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgres://"):]
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args=_connect_args)
else:
    # Serverless-friendly: no pooled connections held between invocations
    from sqlalchemy.pool import NullPool
    engine = create_engine(DATABASE_URL, connect_args=_connect_args, poolclass=NullPool)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    from models import Base as _Base  # noqa
    import models  # noqa: F401  (registers tables)
    Base.metadata.create_all(bind=engine)
    # Tiny additive migration for DBs created before approve_link existed
    # (create_all never alters existing tables). SQLite + Postgres syntax.
    from sqlalchemy import inspect, text
    cols = [c["name"] for c in inspect(engine).get_columns("orders")]
    if "approve_link" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE orders ADD COLUMN approve_link TEXT"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
