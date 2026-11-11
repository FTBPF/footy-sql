import click
from sqlalchemy.exc import OperationalError

from . import db
from . import loading

@click.group()
def main():
    """Football league tables on PostgreSQL."""
    pass


@main.group('db')
def db_group():
    """Manage the database schema."""
    pass


@db_group.command()
@click.option(
    "--drop",
    is_flag=True,
    help='Drop existing schema before initializing.'
)
def init(drop):
    """Create the schema (does nothing if it already exists)."""
    engine = db.get_engine()
    try:
        if drop:
            click.confirm(
                "This deletes all footy tables and their data. Continue?",
                abort=True,
            )
            db.drop_schema(engine)
            click.echo('Dropped existing schema.')
        created = db.init_schema(engine)
    except OperationalError:
        raise click.ClickException("Cannot connect to the database.")
    if created:
        click.echo("Schema created.")
    else:
        click.echo("Schema already exists.")


@main.command()
@click.option(
    "--league",
    required=True,
    help="League name (e.g. SP1)."
)
@click.option(
    "--season",
    required=True,
    help="Season (e.g. 2324)."
)
def load(league, season):
    """Load a league season from csv into the database."""
    engine = db.get_engine()
    try:
        matches, teams = loading.load_season_csv(engine, league, season)
        click.echo(f"Loaded {league}/{season}: {matches} matches, {teams} teams.")
    except Exception as e:
        raise click.ClickException(f"Failed to load season: {e}")
