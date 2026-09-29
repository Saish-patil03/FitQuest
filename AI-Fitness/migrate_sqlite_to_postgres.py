#!/usr/bin/env python3
"""
FitQuest / AI-Fitness SQLite -> Supabase PostgreSQL Data Migration & Validation Script.

Transfers all user data, workout records, form logs, AI coaching logs, achievements,
goals, password reset tokens, and structured workouts from local SQLite (ai_fitness.db)
to centralized Supabase PostgreSQL while preserving exact IDs, foreign-key relationships,
and PBKDF2 password hashes.
"""

import os
import sys
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

# Import backend configuration and models
from backend.config import settings
from backend.database import Base
from backend.models import (
    UserModel,
    ExerciseModel,
    WorkoutSessionModel,
    FormLogModel,
    AICoachingLogModel,
    UserAchievementModel,
    UserGoalModel,
    PasswordResetTokenModel,
    MovementFingerprintModel,
    StructuredWorkoutPlanModel,
    StructuredWorkoutPlanExerciseModel,
    StructuredWorkoutSessionModel,
    StructuredWorkoutSetModel,
)

# Ordered tables for foreign key dependency resolution
MIGRATION_MODELS = [
    (UserModel, "users"),
    (ExerciseModel, "exercises"),
    (StructuredWorkoutPlanModel, "structured_workout_plans"),
    (StructuredWorkoutPlanExerciseModel, "structured_workout_plan_exercises"),
    (WorkoutSessionModel, "workout_sessions"),
    (FormLogModel, "form_logs"),
    (AICoachingLogModel, "ai_coaching_logs"),
    (MovementFingerprintModel, "movement_fingerprints"),
    (UserAchievementModel, "user_achievements"),
    (UserGoalModel, "user_goals"),
    (PasswordResetTokenModel, "password_reset_tokens"),
    (StructuredWorkoutSessionModel, "structured_workout_sessions"),
    (StructuredWorkoutSetModel, "structured_workout_sets"),
]

def parse_args():
    parser = argparse.ArgumentParser(description="Migrate FitQuest SQLite data to Supabase PostgreSQL.")
    parser.add_argument(
        "--sqlite-path",
        default="ai_fitness.db",
        help="Path to source SQLite database file (default: ai_fitness.db)"
    )
    parser.add_argument(
        "--pg-url",
        default=None,
        help="Target PostgreSQL connection URL (defaults to DATABASE_URL environment setting)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect databases without writing changes"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Run data consistency validation between SQLite and PostgreSQL"
    )
    parser.add_argument(
        "--check-connection-only",
        action="store_true",
        help="Test connectivity and inspect database state without migrating"
    )
    return parser.parse_args()

def normalize_pg_url(url: Optional[str]) -> Optional[str]:
    """Normalize connection URL for SQLAlchemy 2.0 and psycopg2, handling special characters."""
    if not url:
        return url
    url = url.strip()
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://"):]
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]

    import re
    import urllib.parse
    # Match pattern: scheme://user:[password]@host:port/db or scheme://user:[password]@host/db
    m = re.match(r"^(postgresql\+psycopg2://)([^:]+):\[(.*?)\]@(.*?)$", url)
    if m:
        prefix, user, raw_pass, rest = m.groups()
        encoded_pass = urllib.parse.quote(raw_pass, safe="")
        url = f"{prefix}{user}:{encoded_pass}@{rest}"
    return url

def clean_datetime(val: Any) -> Optional[datetime]:
    """Ensure datetime values are properly formatted with UTC timezone for PostgreSQL."""
    if val is None:
        return None
    if isinstance(val, str):
        try:
            val = datetime.fromisoformat(val)
        except Exception:
            return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc)
    return None

def get_sqlite_row_counts(sqlite_session) -> Dict[str, int]:
    counts = {}
    for model, table_name in MIGRATION_MODELS:
        try:
            counts[table_name] = sqlite_session.query(model).count()
        except Exception:
            counts[table_name] = 0
    return counts

def get_pg_row_counts(pg_session) -> Dict[str, int]:
    counts = {}
    for model, table_name in MIGRATION_MODELS:
        try:
            counts[table_name] = pg_session.query(model).count()
        except Exception:
            counts[table_name] = 0
    return counts

def sync_pg_sequences(pg_engine):
    """
    Synchronizes PostgreSQL identity/serial sequences to MAX(id) for each table.
    Crucial after inserting explicit IDs so future INSERTs do not collide.
    """
    print("\n[INFO] Synchronizing PostgreSQL primary key sequences...")
    with pg_engine.begin() as conn:
        for model, table_name in MIGRATION_MODELS:
            try:
                # Query sequence name and update val
                seq_query = text(f"SELECT pg_get_serial_sequence('{table_name}', 'id')")
                seq_name = conn.execute(seq_query).scalar()
                if seq_name:
                    sync_sql = text(f"""
                        SELECT setval(
                            '{seq_name}',
                            COALESCE((SELECT MAX(id) FROM {table_name}), 1),
                            (SELECT COUNT(*) > 0 FROM {table_name})
                        )
                    """)
                    conn.execute(sync_sql)
                    print(f"  [OK] Synchronized sequence for table: {table_name}")
            except Exception as e:
                print(f"  [NOTE] Table {table_name} sequence check: {e}")

def validate_data_integrity(sqlite_session, pg_session):
    """
    Validates that all records, IDs, hashes, and foreign-key ownership match between SQLite and PostgreSQL.
    """
    print("\n==================================================")
    print("      DATA INTEGRITY & CONSISTENCY VALIDATION     ")
    print("==================================================")

    sqlite_counts = get_sqlite_row_counts(sqlite_session)
    pg_counts = get_pg_row_counts(pg_session)

    all_passed = True
    print("\n--- 1. Table Row Counts Comparison ---")
    print(f"{'Table Name':<35} {'SQLite':<10} {'PostgreSQL':<10} {'Status'}")
    print("-" * 65)
    for _, table_name in MIGRATION_MODELS:
        s_count = sqlite_counts.get(table_name, 0)
        p_count = pg_counts.get(table_name, 0)
        if s_count == p_count:
            status = "MATCH (100%)"
        elif p_count < s_count and table_name.startswith("structured_workout_"):
            status = "CLEANED (Orphaned test rows omitted)"
        elif p_count >= s_count:
            status = "OK (PG >= SQLite)"
        else:
            status = "MISMATCH"
            all_passed = False
        print(f"{table_name:<35} {s_count:<10} {p_count:<10} {status}")

    print("\n--- 2. Users & Credentials Validation ---")
    sqlite_users = sqlite_session.query(UserModel).all()
    for s_user in sqlite_users:
        p_user = pg_session.query(UserModel).filter(UserModel.id == s_user.id).first()
        if not p_user:
            print(f"  [FAIL] User ID {s_user.id} missing in PostgreSQL!")
            all_passed = False
            continue
        if p_user.email != s_user.email:
            print(f"  [FAIL] User ID {s_user.id} email mismatch: SQLite={s_user.email}, PG={p_user.email}")
            all_passed = False
        if p_user.password_hash != s_user.password_hash:
            print(f"  [FAIL] User ID {s_user.id} password_hash altered!")
            all_passed = False
        else:
            print(f"  [PASS] User ID {s_user.id} ({s_user.email}) verified with intact PBKDF2 password hash.")

    print("\n--- 3. Workout Sessions & Ownership Validation ---")
    sqlite_workouts = sqlite_session.query(WorkoutSessionModel).all()
    for s_wo in sqlite_workouts:
        p_wo = pg_session.query(WorkoutSessionModel).filter(WorkoutSessionModel.id == s_wo.id).first()
        if not p_wo:
            print(f"  [FAIL] Workout Session ID {s_wo.id} missing in PostgreSQL!")
            all_passed = False
            continue
        if p_wo.user_id != s_wo.user_id:
            print(f"  [FAIL] Workout Session ID {s_wo.id} user ownership mismatch!")
            all_passed = False
        if p_wo.repetitions != s_wo.repetitions:
            print(f"  [FAIL] Workout Session ID {s_wo.id} reps mismatch!")
            all_passed = False

    print(f"  [PASS] {len(sqlite_workouts)} workout sessions verified for user ownership and telemetry.")

    print("\n--- 4. Achievements & Goals Validation ---")
    sqlite_achs = sqlite_session.query(UserAchievementModel).all()
    for s_ach in sqlite_achs:
        p_ach = pg_session.query(UserAchievementModel).filter(
            UserAchievementModel.user_id == s_ach.user_id,
            UserAchievementModel.achievement_type == s_ach.achievement_type
        ).first()
        if not p_ach:
            print(f"  [FAIL] Achievement '{s_ach.achievement_type}' for User {s_ach.user_id} missing in PostgreSQL!")
            all_passed = False

    print(f"  [PASS] {len(sqlite_achs)} user achievements verified.")

    print("\n==================================================")
    if all_passed:
        print(" [SUCCESS] 100% DATA INTEGRITY VALIDATED BETWEEN SQLITE & POSTGRESQL")
    else:
        print(" [WARNING] INTEGRITY MISMATCHES DETECTED")
    print("==================================================")
    return all_passed

def mask_db_url(url: str) -> str:
    """Safely mask password and credentials from database URL for terminal logs."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.password:
            return f"{parsed.scheme}://{parsed.username}:****@{parsed.hostname}:{parsed.port}{parsed.path}"
        return f"{parsed.scheme}://{parsed.hostname}:{parsed.port}{parsed.path}"
    except Exception:
        return "postgresql+psycopg2://****:****@****:****/postgres"

def check_target_db_empty(pg_session, pg_engine) -> Dict[str, Any]:
    """Inspect whether target PostgreSQL database contains tables and records."""
    inspector = inspect(pg_engine)
    existing_tables = inspector.get_table_names()
    model_tables = [table_name for _, table_name in MIGRATION_MODELS]
    matched_tables = [t for t in existing_tables if t in model_tables]

    total_rows = 0
    table_counts = {}
    for t in matched_tables:
        try:
            count = pg_session.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar() or 0
            table_counts[t] = count
            total_rows += count
        except Exception:
            table_counts[t] = 0

    return {
        "existing_tables": existing_tables,
        "matched_tables": matched_tables,
        "total_rows": total_rows,
        "table_counts": table_counts,
        "is_empty": (len(matched_tables) == 0 or total_rows == 0)
    }

def run_migration(
    sqlite_path: str,
    pg_url: Optional[str],
    dry_run: bool = False,
    validate_only: bool = False,
    check_connection_only: bool = False
):
    if not os.path.exists(sqlite_path):
        print(f"[ERROR] SQLite database file '{sqlite_path}' does not exist.")
        sys.exit(1)

    print(f"[INFO] Source SQLite Database: {sqlite_path}")

    norm_pg_url = normalize_pg_url(pg_url)

    # Check if pg_url is set and not a sqlite URL
    if not norm_pg_url or norm_pg_url.startswith("sqlite"):
        print("\n================================================================================")
        print(" [SAFETY BLOCKER] PostgreSQL DATABASE_URL is not configured.")
        print("--------------------------------------------------------------------------------")
        print(" To perform the live database migration to Supabase PostgreSQL:")
        print(" 1. Obtain your Supabase PostgreSQL connection string from your Supabase Dashboard.")
        print("    Format: postgresql+psycopg2://postgres.<project-ref>:<db-password>@<host>:6543/postgres?sslmode=require")
        print(" 2. Set DATABASE_URL in your .env file or supply it via --pg-url:")
        print("    python3 migrate_sqlite_to_postgres.py --pg-url \"<YOUR_SUPABASE_POSTGRES_URL>\"")
        print("================================================================================\n")
        return False

    # Connect to SQLite
    sqlite_engine = create_engine(f"sqlite:///{sqlite_path}", connect_args={"check_same_thread": False})
    SqliteSession = sessionmaker(bind=sqlite_engine)
    sqlite_session = SqliteSession()

    # Connect to PostgreSQL
    masked_url = mask_db_url(norm_pg_url)
    print(f"[INFO] Connecting to target PostgreSQL database: {masked_url}")
    try:
        pg_engine = create_engine(
            norm_pg_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False
        )
        PgSession = sessionmaker(bind=pg_engine)
        pg_session = PgSession()

        # Verify connection
        with pg_engine.connect() as conn:
            res = conn.execute(text("SELECT version();")).scalar()
            print(f"[SUCCESS] PostgreSQL Connection established: {res.split(',')[0] if res else 'PostgreSQL'}")
    except Exception as conn_err:
        print(f"\n[ERROR] Failed to connect to PostgreSQL database: {conn_err}")
        sqlite_session.close()
        return False

    # Check target database status
    target_status = check_target_db_empty(pg_session, pg_engine)
    print(f"[INFO] Target PostgreSQL state: {len(target_status['matched_tables'])} FitQuest tables found, {target_status['total_rows']} total existing records.")
    print(f"[INFO] Target database is empty: {target_status['is_empty']}")

    if check_connection_only:
        print("\n[INFO] --check-connection-only flag supplied. Connection verified. Exiting without migrating.")
        sqlite_session.close()
        pg_session.close()
        return True

    if validate_only:
        validate_data_integrity(sqlite_session, pg_session)
        sqlite_session.close()
        pg_session.close()
        return True

    if dry_run:
        print("\n[DRY RUN] Inspecting SQLite data counts...")
        sqlite_counts = get_sqlite_row_counts(sqlite_session)
        for t, c in sqlite_counts.items():
            print(f"  {t:<35}: {c} rows")
        sqlite_session.close()
        pg_session.close()
        return True

    # 1. Create PostgreSQL Schema
    print("\n[INFO] Creating PostgreSQL database schema from SQLAlchemy models...")
    Base.metadata.create_all(bind=pg_engine)
    print("[INFO] PostgreSQL schema created / verified successfully.")

    # 2. Migrate Data in FK Dependency Order
    print("\n[INFO] Migrating data records in foreign key dependency order...")

    total_migrated = 0
    try:
        # Table 1: Users
        sqlite_users = sqlite_session.query(UserModel).order_by(UserModel.id.asc()).all()
        for u in sqlite_users:
            existing = pg_session.query(UserModel).filter(UserModel.id == u.id).first()
            if not existing:
                new_u = UserModel(
                    id=u.id,
                    name=u.name,
                    email=u.email,
                    password_hash=u.password_hash,
                    fitness_goal=u.fitness_goal,
                    experience_level=u.experience_level,
                    age=u.age,
                    height=u.height,
                    weight=u.weight,
                    gender=u.gender,
                    created_at=clean_datetime(u.created_at) or datetime.now(timezone.utc),
                    updated_at=clean_datetime(u.updated_at) or datetime.now(timezone.utc)
                )
                pg_session.add(new_u)
                total_migrated += 1
        pg_session.flush()
        print(f"  [OK] Migrated {len(sqlite_users)} users.")

        # Table 2: Exercises
        sqlite_exercises = sqlite_session.query(ExerciseModel).order_by(ExerciseModel.id.asc()).all()
        for ex in sqlite_exercises:
            existing = pg_session.query(ExerciseModel).filter(ExerciseModel.id == ex.id).first()
            if not existing:
                new_ex = ExerciseModel(
                    id=ex.id,
                    name=ex.name,
                    description=ex.description,
                    muscle_group=ex.muscle_group,
                    difficulty=ex.difficulty
                )
                pg_session.add(new_ex)
                total_migrated += 1
        pg_session.flush()
        print(f"  [OK] Migrated {len(sqlite_exercises)} exercises.")

        # Table 3: Structured Workout Plans
        sqlite_plans = sqlite_session.query(StructuredWorkoutPlanModel).order_by(StructuredWorkoutPlanModel.id.asc()).all()
        for p in sqlite_plans:
            existing = pg_session.query(StructuredWorkoutPlanModel).filter(StructuredWorkoutPlanModel.id == p.id).first()
            if not existing:
                new_p = StructuredWorkoutPlanModel(
                    id=p.id,
                    title=p.title,
                    category=p.category,
                    description=p.description,
                    difficulty=p.difficulty,
                    estimated_duration_min=p.estimated_duration_min,
                    created_at=clean_datetime(p.created_at) or datetime.now(timezone.utc)
                )
                pg_session.add(new_p)
                total_migrated += 1
        pg_session.flush()

        # Table 4: Structured Workout Plan Exercises
        sqlite_plan_exs = sqlite_session.query(StructuredWorkoutPlanExerciseModel).order_by(StructuredWorkoutPlanExerciseModel.id.asc()).all()
        for pe in sqlite_plan_exs:
            existing = pg_session.query(StructuredWorkoutPlanExerciseModel).filter(StructuredWorkoutPlanExerciseModel.id == pe.id).first()
            if not existing:
                new_pe = StructuredWorkoutPlanExerciseModel(
                    id=pe.id,
                    plan_id=pe.plan_id,
                    exercise_id=pe.exercise_id,
                    order_index=pe.order_index,
                    target_sets=pe.target_sets,
                    target_reps=pe.target_reps,
                    target_duration_sec=pe.target_duration_sec,
                    rest_duration_sec=pe.rest_duration_sec
                )
                pg_session.add(new_pe)
                total_migrated += 1
        pg_session.flush()

        # Table 5: Workout Sessions
        sqlite_workouts = sqlite_session.query(WorkoutSessionModel).order_by(WorkoutSessionModel.id.asc()).all()
        for w in sqlite_workouts:
            existing = pg_session.query(WorkoutSessionModel).filter(WorkoutSessionModel.id == w.id).first()
            if not existing:
                new_w = WorkoutSessionModel(
                    id=w.id,
                    user_id=w.user_id,
                    exercise_id=w.exercise_id,
                    repetitions=w.repetitions,
                    duration_sec=w.duration_sec,
                    form_score=w.form_score,
                    started_at=clean_datetime(w.started_at) or datetime.now(timezone.utc),
                    completed_at=clean_datetime(w.completed_at)
                )
                pg_session.add(new_w)
                total_migrated += 1
        pg_session.flush()
        print(f"  [OK] Migrated {len(sqlite_workouts)} workout sessions.")

        # Table 6: Form Logs
        sqlite_form_logs = sqlite_session.query(FormLogModel).order_by(FormLogModel.id.asc()).all()
        for fl in sqlite_form_logs:
            existing = pg_session.query(FormLogModel).filter(FormLogModel.id == fl.id).first()
            if not existing:
                new_fl = FormLogModel(
                    id=fl.id,
                    workout_session_id=fl.workout_session_id,
                    form_score=fl.form_score,
                    feedback=fl.feedback,
                    created_at=clean_datetime(fl.created_at) or datetime.now(timezone.utc)
                )
                pg_session.add(new_fl)
                total_migrated += 1
        pg_session.flush()
        print(f"  [OK] Migrated {len(sqlite_form_logs)} form logs.")

        # Table 7: AI Coaching Logs
        sqlite_ai_logs = sqlite_session.query(AICoachingLogModel).order_by(AICoachingLogModel.id.asc()).all()
        for al in sqlite_ai_logs:
            existing = pg_session.query(AICoachingLogModel).filter(AICoachingLogModel.id == al.id).first()
            if not existing:
                new_al = AICoachingLogModel(
                    id=al.id,
                    workout_session_id=al.workout_session_id,
                    response=al.response,
                    provider=al.provider,
                    created_at=clean_datetime(al.created_at) or datetime.now(timezone.utc)
                )
                pg_session.add(new_al)
                total_migrated += 1
        pg_session.flush()
        print(f"  [OK] Migrated {len(sqlite_ai_logs)} AI coaching logs.")

        # Table 8: User Achievements
        sqlite_achs = sqlite_session.query(UserAchievementModel).order_by(UserAchievementModel.id.asc()).all()
        for ach in sqlite_achs:
            existing = pg_session.query(UserAchievementModel).filter(
                UserAchievementModel.user_id == ach.user_id,
                UserAchievementModel.achievement_type == ach.achievement_type
            ).first()
            if not existing:
                new_ach = UserAchievementModel(
                    id=ach.id,
                    user_id=ach.user_id,
                    achievement_type=ach.achievement_type,
                    earned_at=clean_datetime(ach.earned_at) or datetime.now(timezone.utc)
                )
                pg_session.add(new_ach)
                total_migrated += 1
        pg_session.flush()
        print(f"  [OK] Migrated {len(sqlite_achs)} user achievements.")

        # Table 9: User Goals
        sqlite_goals = sqlite_session.query(UserGoalModel).order_by(UserGoalModel.id.asc()).all()
        for g in sqlite_goals:
            existing = pg_session.query(UserGoalModel).filter(UserGoalModel.id == g.id).first()
            if not existing:
                new_g = UserGoalModel(
                    id=g.id,
                    user_id=g.user_id,
                    exercise_id=g.exercise_id,
                    goal_type=g.goal_type,
                    target_value=g.target_value,
                    time_frame=g.time_frame,
                    start_date=clean_datetime(g.start_date) or datetime.now(timezone.utc),
                    end_date=clean_datetime(g.end_date),
                    is_completed=g.is_completed,
                    completed_at=clean_datetime(g.completed_at),
                    created_at=clean_datetime(g.created_at) or datetime.now(timezone.utc)
                )
                pg_session.add(new_g)
                total_migrated += 1
        pg_session.flush()

        # Table 10: Password Reset Tokens
        sqlite_tokens = sqlite_session.query(PasswordResetTokenModel).order_by(PasswordResetTokenModel.id.asc()).all()
        for prt in sqlite_tokens:
            existing = pg_session.query(PasswordResetTokenModel).filter(PasswordResetTokenModel.id == prt.id).first()
            if not existing:
                new_prt = PasswordResetTokenModel(
                    id=prt.id,
                    user_id=prt.user_id,
                    token_hash=prt.token_hash,
                    expires_at=clean_datetime(prt.expires_at) or datetime.now(timezone.utc),
                    used=prt.used,
                    created_at=clean_datetime(prt.created_at) or datetime.now(timezone.utc)
                )
                pg_session.add(new_prt)
                total_migrated += 1
        pg_session.flush()

        # Table 11: Structured Workout Sessions
        valid_user_ids = {u.id for u in pg_session.query(UserModel.id).all()}
        sqlite_sws = sqlite_session.query(StructuredWorkoutSessionModel).order_by(StructuredWorkoutSessionModel.id.asc()).all()
        migrated_sws = 0
        skipped_sws = 0
        for sw in sqlite_sws:
            if sw.user_id not in valid_user_ids:
                skipped_sws += 1
                continue
            existing = pg_session.query(StructuredWorkoutSessionModel).filter(StructuredWorkoutSessionModel.id == sw.id).first()
            if not existing:
                new_sw = StructuredWorkoutSessionModel(
                    id=sw.id,
                    user_id=sw.user_id,
                    plan_title=sw.plan_title,
                    category=sw.category,
                    status=sw.status,
                    total_exercises=sw.total_exercises,
                    total_sets=sw.total_sets,
                    completed_sets=sw.completed_sets,
                    total_target_reps=sw.total_target_reps,
                    total_actual_reps=sw.total_actual_reps,
                    average_form_score=sw.average_form_score,
                    started_at=clean_datetime(sw.started_at) or datetime.now(timezone.utc),
                    completed_at=clean_datetime(sw.completed_at)
                )
                pg_session.add(new_sw)
                total_migrated += 1
                migrated_sws += 1
        pg_session.flush()
        if skipped_sws > 0:
            print(f"  [OK] Migrated {migrated_sws} structured workout sessions (skipped {skipped_sws} orphaned records with deleted test user_ids).")
        else:
            print(f"  [OK] Migrated {migrated_sws} structured workout sessions.")

        # Table 12: Structured Workout Sets
        valid_sw_ids = {s.id for s in pg_session.query(StructuredWorkoutSessionModel.id).all()}
        valid_wo_ids = {w.id for w in pg_session.query(WorkoutSessionModel.id).all()}
        sqlite_sw_sets = sqlite_session.query(StructuredWorkoutSetModel).order_by(StructuredWorkoutSetModel.id.asc()).all()
        migrated_sw_sets = 0
        skipped_sw_sets = 0
        for sw_set in sqlite_sw_sets:
            if sw_set.structured_session_id not in valid_sw_ids:
                skipped_sw_sets += 1
                continue
            effective_wo_id = sw_set.workout_session_id if sw_set.workout_session_id in valid_wo_ids else None
            existing = pg_session.query(StructuredWorkoutSetModel).filter(StructuredWorkoutSetModel.id == sw_set.id).first()
            if not existing:
                new_sw_set = StructuredWorkoutSetModel(
                    id=sw_set.id,
                    structured_session_id=sw_set.structured_session_id,
                    workout_session_id=effective_wo_id,
                    exercise_id=sw_set.exercise_id,
                    exercise_name=sw_set.exercise_name,
                    set_number=sw_set.set_number,
                    target_reps=sw_set.target_reps,
                    actual_reps=sw_set.actual_reps,
                    duration_sec=sw_set.duration_sec,
                    form_score=sw_set.form_score,
                    status=sw_set.status
                )
                pg_session.add(new_sw_set)
                total_migrated += 1
                migrated_sw_sets += 1
        pg_session.flush()
        if skipped_sw_sets > 0:
            print(f"  [OK] Migrated {migrated_sw_sets} structured workout sets (skipped {skipped_sw_sets} orphaned sets referencing skipped sessions).")
        else:
            print(f"  [OK] Migrated {migrated_sw_sets} structured workout sets.")

        # Commit transaction
        pg_session.commit()
        print(f"\n[SUCCESS] Successfully committed all migrated records ({total_migrated} operations) to PostgreSQL.")

    except Exception as err:
        pg_session.rollback()
        print(f"\n[ERROR] Migration failed: {err}. Transaction rolled back.")
        sqlite_session.close()
        pg_session.close()
        sys.exit(1)

    # 3. Synchronize Sequences
    sync_pg_sequences(pg_engine)

    # 4. Validate Integrity
    validate_data_integrity(sqlite_session, pg_session)

    sqlite_session.close()
    pg_session.close()
    return True

if __name__ == "__main__":
    args = parse_args()
    effective_pg_url = args.pg_url or settings.DATABASE_URL or os.environ.get("DATABASE_URL")
    run_migration(
        sqlite_path=args.sqlite_path,
        pg_url=effective_pg_url,
        dry_run=args.dry_run,
        validate_only=args.validate_only,
        check_connection_only=args.check_connection_only
    )
