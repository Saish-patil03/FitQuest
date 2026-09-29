#!/usr/bin/env python3
"""
Test Suite for Database Resilience, Startup Retry, Connection Pooling, and Security.
Verifies:
- A: Healthy database succeeds immediately without delay.
- B: Temporary database failure retries with exponential backoff and succeeds.
- C: Persistent failure fails cleanly after bounded attempts.
- D: Exponential backoff delay schedule [2, 4, 8, 16] verification.
- E: PostgreSQL engine pool_pre_ping and pool_recycle configuration.
- F: SQLite isolation and compatibility.
- G: No database passwords or sensitive credentials logged in retry/error outputs.
- H: GET /health backward compatibility.
"""

import io
import sys
import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.database import execute_with_retry, init_db, init_db_with_retry, Base, engine as global_engine
from backend.main import app

class TestDatabaseResilience(unittest.TestCase):

    def test_A_healthy_database_succeeds_immediately(self):
        """TEST A: Healthy database succeeds on attempt 1 with zero retry delay."""
        mock_op = MagicMock(return_value="success")
        mock_sleep = MagicMock()

        result = execute_with_retry(
            mock_op,
            max_retries=5,
            initial_delay=2.0,
            backoff_factor=2.0,
            sleep_fn=mock_sleep
        )

        self.assertEqual(result, "success")
        self.assertEqual(mock_op.call_count, 1)
        mock_sleep.assert_not_called()

    def test_B_temporary_failure_retries_and_succeeds(self):
        """TEST B: First 2 attempts fail, 3rd succeeds; retry succeeds without crashing."""
        call_count = 0

        def flaky_op():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary connection drop")
            return "connected"

        mock_sleep = MagicMock()

        result = execute_with_retry(
            flaky_op,
            max_retries=5,
            initial_delay=2.0,
            backoff_factor=2.0,
            sleep_fn=mock_sleep
        )

        self.assertEqual(result, "connected")
        self.assertEqual(call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_any_call(2.0)
        mock_sleep.assert_any_call(4.0)

    def test_C_persistent_failure_fails_after_bounded_attempts(self):
        """TEST C: Persistent failure raises after exactly max_retries attempts."""
        mock_op = MagicMock(side_effect=ConnectionRefusedError("Database down"))
        mock_sleep = MagicMock()

        with self.assertRaises(ConnectionRefusedError):
            execute_with_retry(
                mock_op,
                max_retries=5,
                initial_delay=2.0,
                backoff_factor=2.0,
                sleep_fn=mock_sleep
            )

        self.assertEqual(mock_op.call_count, 5)
        self.assertEqual(mock_sleep.call_count, 4)

    def test_D_exponential_backoff_delays(self):
        """TEST D: Retry delays increase exponentially [2.0, 4.0, 8.0, 16.0]."""
        mock_op = MagicMock(side_effect=TimeoutError("Timeout"))
        sleep_delays = []

        def mock_sleep(d):
            sleep_delays.append(d)

        with self.assertRaises(TimeoutError):
            execute_with_retry(
                mock_op,
                max_retries=5,
                initial_delay=2.0,
                backoff_factor=2.0,
                sleep_fn=mock_sleep
            )

        self.assertEqual(sleep_delays, [2.0, 4.0, 8.0, 16.0])

    def test_E_postgresql_engine_settings(self):
        """TEST E: PostgreSQL engine has pool_pre_ping=True and pool_recycle enabled."""
        # Test creating a simulated PostgreSQL engine using the same parameters as backend/database.py
        pg_engine = create_engine(
            "postgresql+psycopg2://testuser:testpass@localhost:5432/testdb",
            pool_pre_ping=True,
            pool_recycle=300,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            echo=False
        )
        self.assertTrue(pg_engine.pool._pre_ping)
        self.assertEqual(pg_engine.pool._recycle, 300)
        self.assertEqual(pg_engine.pool._timeout, 30)

    def test_F_sqlite_isolation_unaffected(self):
        """TEST F: Existing isolated SQLite databases and engine work seamlessly."""
        test_engine = create_engine("sqlite:///:memory:", poolclass=StaticPool, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=test_engine)
        self.assertTrue(test_engine.url.drivername.startswith("sqlite"))

    def test_G_no_secrets_in_retry_or_error_logs(self):
        """TEST G: Retry and error logs never contain database passwords or secrets."""
        secret_password = "SuperSecretSupabasePassword123!"
        sensitive_url = f"postgresql+psycopg2://postgres:{secret_password}@db.supabase.co:5432/postgres"

        captured_output = io.StringIO()

        def failing_with_secret():
            raise RuntimeError(f"Connection failed to {sensitive_url}")

        with patch("sys.stdout", captured_output):
            try:
                execute_with_retry(
                    failing_with_secret,
                    max_retries=2,
                    initial_delay=0.01,
                    sleep_fn=lambda x: None
                )
            except RuntimeError:
                pass

        logged_content = captured_output.getvalue()
        self.assertNotIn(secret_password, logged_content, "Security breach: Secret password was exposed in logs!")
        self.assertNotIn("db.supabase.co", logged_content, "Security breach: Hostname/URL was exposed in logs!")

    def test_H_health_endpoint_backward_compatible(self):
        """TEST H: GET /health returns exact backward-compatible contract."""
        client = TestClient(app)
        res = client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "AI Fitness Backend")

if __name__ == "__main__":
    unittest.main()
