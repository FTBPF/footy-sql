import click
import pandas as pd
from sqlalchemy.exc import OperationalError

from . import db
from . import loading
from . import standings

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
@click.option(
    "--as-of",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Calculate standings up to this date (YYYY-MM-DD)."
)
def table(league, season, as_of):
    """Display the league standings."""
    engine = db.get_engine()
    try:
        rows = standings.get_standings(engine, league, season, as_of)
    except Exception as e:
        raise click.ClickException(f"Failed to display the league standings: {e}")
    
    if not rows:
        click.echo(f"No matches found for this league: {league}, season: {season} and date: {as_of.date()}.")
    else:
        table_df = pd.DataFrame(([dict(row) for row in rows]))
        click.echo(table_df.to_string(index=False))
