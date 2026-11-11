import os
import pathlib
import sqlalchemy as sa

DEFAULT_URL = 'postgresql+psycopg://'
TABLES = ['match', 'season', 'team', 'league']


def get_engine():
    return sa.create_engine(os.environ.get('FOOTY_DB_URL', DEFAULT_URL))


def query(engine, sql, **params):
    with engine.connect() as conn:
        return conn.execute(sa.text(sql), params).mappings().all()


def drop_schema(engine):
    with engine.begin() as conn:
        for table in TABLES:            
            conn.execute(sa.text(f"DROP TABLE IF EXISTS {table} CASCADE;"))


def init_schema(engine):
    inspector = sa.inspect(engine)

    if inspector.has_table("match"):
        return False

    schema_path = pathlib.Path(__file__).parent / "schema.sql"
    schema_sql = schema_path.read_text()

    with engine.begin() as conn:
        conn.execute(sa.text(schema_sql))

    return True
