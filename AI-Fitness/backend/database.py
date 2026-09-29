import time
import logging
import re
import urllib.parse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import settings

logger = logging.getLogger("backend.database")

# Normalize database URL scheme for SQLAlchemy 2.0 + psycopg2
db_url = settings.DATABASE_URL.strip() if settings.DATABASE_URL else ""
if db_url.startswith("postgres://"):
    db_url = "postgresql+psycopg2://" + db_url[len("postgres://"):]
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
    db_url = "postgresql+psycopg2://" + db_url[len("postgresql://"):]

# Sanitize bracketed passwords if present: scheme://user:[password]@host:port/db
m = re.match(r"^(postgresql\+psycopg2://)([^:]+):\[(.*?)\]@(.*?)$", db_url)
if m:
    prefix, user, raw_pass, rest = m.groups()
    encoded_pass = urllib.parse.quote(raw_pass, safe="")
    db_url = f"{prefix}{user}:{encoded_pass}@{rest}"

# Configure engine arguments based on database dialect
is_sqlite = db_url.startswith("sqlite")

if is_sqlite:
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        echo=False
    )
else:
    # Production PostgreSQL connection pool configuration
    engine = create_engine(
        db_url,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        echo=False
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

def get_db():
    """
    FastAPI dependency that yields a SQLAlchemy database session.
    Automatically closes session after request completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 20 default registered exercises decoupled from CV ExerciseRegistry
DEFAULT_EXERCISES = [
    ("1", "Bicep Curl"),
    ("2", "Squat"),
    ("3", "Push-up"),
    ("4", "Lunges"),
    ("5", "Shoulder Press"),
    ("6", "Jumping Jacks"),
    ("7", "High Knees"),
    ("8", "Mountain Climbers"),
    ("9", "Plank"),
    ("10", "Glute Bridge"),
    ("11", "Sit-ups"),
    ("12", "Crunches"),
    ("13", "Leg Raises"),
    ("14", "Russian Twists"),
    ("15", "Bicycle Crunches"),
    ("16", "Side Lunges"),
    ("17", "Calf Raises"),
    ("18", "Front Raises"),
    ("19", "Lateral Raises"),
    ("20", "Tricep Extensions"),
]

def seed_exercises(db):
    """
    Idempotently seeds the 20 exercises into the exercises table.
    """
    from backend.models.exercise import ExerciseModel

    seeded_count = 0

    for key, name in DEFAULT_EXERCISES:
        existing = db.query(ExerciseModel).filter(ExerciseModel.name == name).first()
        if not existing:
            exercise = ExerciseModel(
                name=name,
                description=f"{name} exercise tracker powered by YOLO Pose",
                difficulty="Intermediate"
            )
            db.add(exercise)
            seeded_count += 1

    if seeded_count > 0:
        db.commit()
        print(f"[INFO] Seeded {seeded_count} new exercises into the database.")

def _migrate_user_table():
    """
    Ensures newly added user columns exist in users table across dialects.
    """
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if "users" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("users")]
        with engine.begin() as conn:
            if "password_hash" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))
            if "age" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN age INTEGER"))
            if "height" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN height FLOAT"))
            if "weight" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN weight FLOAT"))
            if "gender" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN gender VARCHAR(50)"))
            if "updated_at" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP" if not is_sqlite else "ALTER TABLE users ADD COLUMN updated_at DATETIME"))
            if "leaderboard_visible" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN leaderboard_visible BOOLEAN DEFAULT TRUE"))

def execute_with_retry(
    operation,
    max_retries: int = 5,
    initial_delay: float = 2.0,
    backoff_factor: float = 2.0,
    sleep_fn=time.sleep
):
    """
    Executes a callable database operation with bounded exponential backoff retries.

    Attempt 1: immediate
    If fails: wait initial_delay (~2s)
    Attempt 2: wait initial_delay * 2 (~4s)
    Attempt 3: wait initial_delay * 4 (~8s)
    Attempt 4: wait initial_delay * 8 (~16s)
    Attempt 5: fail clearly

    Never logs credentials, passwords, or connection URIs.
    """
    attempt = 1
    delay = initial_delay

    while attempt <= max_retries:
        try:
            result = operation()
            if attempt > 1:
                logger.info("Database connection established.")
                print("[INFO] Database connection established.")
            return result
        except Exception as exc:
            exc_type = type(exc).__name__
            if attempt < max_retries:
                msg = f"Database connection unavailable ({exc_type}). Retrying in {int(delay)} seconds..."
                logger.warning(msg)
                print(f"[WARN] {msg}")
                sleep_fn(delay)
                delay *= backoff_factor
                attempt += 1
            else:
                msg = f"Database connection failed after {max_retries} attempts."
                logger.error(msg)
                print(f"[ERROR] {msg}")
                raise

def init_db(max_retries: int = 5, initial_delay: float = 2.0, backoff_factor: float = 2.0, sleep_fn=time.sleep):
    """
    Creates database tables and triggers idempotent seed routines with bounded exponential backoff retry.
    """
    def _do_init():
        # Test basic connectivity first
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        # Import all models to ensure they are registered with Base metadata
        import backend.models  # noqa: F401

        Base.metadata.create_all(bind=engine)
        _migrate_user_table()

        db = SessionLocal()
        try:
            seed_exercises(db)
        finally:
            db.close()

    if max_retries > 1:
        execute_with_retry(
            _do_init,
            max_retries=max_retries,
            initial_delay=initial_delay,
            backoff_factor=backoff_factor,
            sleep_fn=sleep_fn
        )
    else:
        _do_init()

def init_db_with_retry(max_retries: int = 5, initial_delay: float = 2.0, backoff_factor: float = 2.0, sleep_fn=time.sleep):
    """
    Convenience alias for startup database initialization with bounded exponential backoff retries.
    """
    return init_db(max_retries=max_retries, initial_delay=initial_delay, backoff_factor=backoff_factor, sleep_fn=sleep_fn)



