from pathlib import Path
import unittest


BACKEND_DIR = Path(__file__).resolve().parents[1]


class AlembicConfigTests(unittest.TestCase):
    def test_alembic_scaffold_exists_for_schema_evolution(self) -> None:
        self.assertTrue((BACKEND_DIR / "alembic.ini").exists())
        self.assertTrue((BACKEND_DIR / "alembic" / "env.py").exists())
        self.assertTrue(
            (BACKEND_DIR / "alembic" / "versions" / "0001_initial_schema.py").exists()
        )

    def test_initial_migration_baselines_current_model_metadata(self) -> None:
        migration = (BACKEND_DIR / "alembic" / "versions" / "0001_initial_schema.py").read_text()
        self.assertIn('revision: str = "0001_initial_schema"', migration)
        self.assertIn('CREATE EXTENSION IF NOT EXISTS vector', migration)
        self.assertIn('Base.metadata.create_all(bind=bind)', migration)
        self.assertIn('from app.models import', migration)

    def test_env_uses_database_url_without_importing_runtime_settings(self) -> None:
        env = (BACKEND_DIR / "alembic" / "env.py").read_text()
        self.assertIn('os.getenv("DATABASE_URL")', env)
        self.assertIn('target_metadata = Base.metadata', env)
        self.assertNotIn('Settings(', env)


if __name__ == "__main__":
    unittest.main()
