"""
Global pytest fixtures.
Ensures all tests run from the project root so relative config paths resolve.
"""
import os
import pytest


@pytest.fixture(autouse=True)
def project_root():
    """Change working directory to project root before every test."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    original = os.getcwd()
    os.chdir(root)
    yield
    os.chdir(original)


@pytest.fixture
def isolated_db(monkeypatch, tmp_path):
    """
    Give each test its own throwaway SQLite database.
    Patches src.database.DB_PATH so the production ledger is never touched.
    """
    import src.database as db_module
    from src.database import init_db

    test_db = str(tmp_path / "test_ledger.db")
    monkeypatch.setattr(db_module, "DB_PATH", test_db)
    init_db()
    return test_db
