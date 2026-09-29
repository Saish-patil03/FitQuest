#!/usr/bin/env python3
"""
Test suite for Phase 4 Step 3: Database Schema, ORM Models, Relationships & Seeding.
"""

from sqlalchemy import inspect, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.database import Base, seed_exercises
from backend.models import (
    UserModel,
    ExerciseModel,
    WorkoutSessionModel,
    FormLogModel,
    AICoachingLogModel
)

def test_database_schema_and_models():
    print("[TEST] Initializing Database Schema & ORM Models test...")

    # Setup isolated in-memory SQLite database
    TEST_DB_URL = "sqlite:///:memory:"
    test_engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Safety Guard: Ensure test only runs against SQLite
    assert str(test_engine.url).startswith("sqlite"), "Safety guard: Tests must only run against SQLite!"

    # 1. Initialize Database Tables & Seed Exercises on isolated engine
    Base.metadata.create_all(bind=test_engine)
    init_db_sess = TestingSessionLocal()
    seed_exercises(init_db_sess)
    init_db_sess.close()
    print("[PASS] Database initialized successfully.")

    # 2. Verify all 5 tables exist in the database
    inspector = inspect(test_engine)
    table_names = inspector.get_table_names()
    expected_tables = ["users", "exercises", "workout_sessions", "form_logs", "ai_coaching_logs"]
    for table in expected_tables:
        assert table in table_names, f"Expected table '{table}' missing from database schema!"
    print(f"[PASS] All 5 database tables verified: {table_names}")

    db = TestingSessionLocal()
    try:
        # 3. Test User Creation
        user = UserModel(
            name="Test Athlete",
            email="athlete@example.com",
            fitness_goal="Hypertrophy",
            experience_level="Intermediate"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        assert user.id is not None, "User ID not generated"
        print(f"[PASS] User created successfully: ID {user.id} ({user.name})")

        # 4. Verify Exercise Seeding & Retrieval (Check 20 exercises from registry)
        exercises = db.query(ExerciseModel).all()
        assert len(exercises) == 20, f"Expected 20 seeded exercises, found {len(exercises)}"
        print(f"[PASS] Verified 20 seeded exercises in DB catalogue.")

        # Test Idempotent Seed Execution (Running seed again should not duplicate)
        seed_exercises(db)
        exercises_after = db.query(ExerciseModel).all()
        assert len(exercises_after) == 20, f"Idempotency failed: expected 20 exercises, got {len(exercises_after)}"
        print("[PASS] Idempotent exercise seed verified (no duplicate entries created).")

        squat_ex = db.query(ExerciseModel).filter_by(name="Squat").first()
        assert squat_ex is not None, "Squat exercise not found in database"

        # 5. Test WorkoutSession referencing User & Exercise
        workout = WorkoutSessionModel(
            user_id=user.id,
            exercise_id=squat_ex.id,
            repetitions=15,
            duration_sec=90,
            form_score=93.3
        )
        db.add(workout)
        db.commit()
        db.refresh(workout)
        assert workout.id is not None, "WorkoutSession ID not generated"
        assert workout.user.name == "Test Athlete", "User relationship failed"
        assert workout.exercise.name == "Squat", "Exercise relationship failed"
        print(f"[PASS] WorkoutSession created: ID {workout.id} for User {workout.user.name} doing {workout.exercise.name}")

        # 6. Test FormLog referencing WorkoutSession
        form_log1 = FormLogModel(workout_session_id=workout.id, form_score=100.0, feedback="Good form")
        form_log2 = FormLogModel(workout_session_id=workout.id, form_score=0.0, feedback="Squat deeper next time")
        db.add_all([form_log1, form_log2])
        db.commit()
        
        db.refresh(workout)
        assert len(workout.form_logs) == 2, f"Expected 2 form logs, got {len(workout.form_logs)}"
        print("[PASS] FormLogs linked to WorkoutSession successfully.")

        # 7. Test AICoachingLog referencing WorkoutSession
        ai_log = AICoachingLogModel(
            workout_session_id=workout.id,
            response="Great squat depth! Focus on keeping core braced.",
            provider="Gemini"
        )
        db.add(ai_log)
        db.commit()

        db.refresh(workout)
        assert len(workout.ai_coaching_logs) == 1, "Expected 1 AI coaching log"
        assert workout.ai_coaching_logs[0].provider == "Gemini", "AI provider mismatch"
        print("[PASS] AICoachingLog linked to WorkoutSession successfully.")

        # 8. Test Cascade Delete behavior (Deleting user should cascade delete session, form logs, AI logs)
        user_id = user.id
        session_id = workout.id
        db.delete(user)
        db.commit()

        orphan_session = db.query(WorkoutSessionModel).filter_by(id=session_id).first()
        orphan_form_logs = db.query(FormLogModel).filter_by(workout_session_id=session_id).all()
        orphan_ai_logs = db.query(AICoachingLogModel).filter_by(workout_session_id=session_id).all()

        assert orphan_session is None, "Cascade delete failed for WorkoutSession"
        assert len(orphan_form_logs) == 0, "Cascade delete failed for FormLogs"
        assert len(orphan_ai_logs) == 0, "Cascade delete failed for AICoachingLogs"
        print("[PASS] Cascade deletion verified (Deleting user cleaned up all child records).")

    finally:
        db.close()

    print("\n[SUCCESS] All Phase 4 Step 3 Database & ORM tests passed cleanly!")

if __name__ == "__main__":
    test_database_schema_and_models()
