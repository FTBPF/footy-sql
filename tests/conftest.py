import os
import pytest
import sqlalchemy as sa
from footy_sql.db import init_schema, TABLES


@pytest.fixture(scope="session")
def test_engine():
    """Cria o engine apontado à base de dados de testes."""
    test_url = os.getenv("FOOTY_TEST_DB_URL")
    
    if not test_url:
        pytest.fail(
            "FOOTY_TEST_DB_URL environment variable is not set. "
            "Refusing to run tests against development database."
        )
    
    if "ff.footy-sql" in test_url and "test" not in test_url:
        pytest.fail(
            f"SAFETY ERROR: FOOTY_TEST_DB_URL ('{test_url}') appears to point "
            "to the development database! Aborting tests."
        )
    
    engine = sa.create_engine(test_url)
    
    with engine.begin() as conn:
        for table in TABLES:
            conn.execute(sa.text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
    
    init_schema(engine)
    return engine


@pytest.fixture(autouse=True)
def clean_database(test_engine):
    """Limpa (trunca) todas as tabelas antes de cada teste individual."""
    with test_engine.begin() as conn:
        tables_str = ", ".join(TABLES)
        conn.execute(sa.text(f"TRUNCATE TABLE {tables_str} RESTART IDENTITY CASCADE;"))
