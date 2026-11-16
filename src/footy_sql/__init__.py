import click
import pandas as pd
from sqlalchemy.exc import OperationalError

from . import db, loading, standings, stats, recording

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
    except OperationalError as e:
        raise click.ClickException(f"Cannot connect to the database: {e}")
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


@main.command()
@click.option(
    "--league",
    type=str,
    help="Name of the League for home-advantage check.",
)
@click.option(
    "--season",
    type=int,
    help="Which season for home-advantage check.",
)
def home_advantage(league, season):
    """Show the home, draw and away win percentage."""
    engine = db.get_engine()
    try:
        home, draw, away = stats.get_home_advantage_percentage(engine, league, season)
    except Exception as e:
        raise click.ClickException(f"Failed to display the home-advantage percentage: {e}")
    click.echo(f"Home win: {home:.1f}%  Draw: {draw:.1f}%  Away win: {away:.1f}%")


@main.command()
@click.option(
    "--league",
    required=True,
    type=str,
    help="League name (e.g. SP1)."
)
@click.option(
    "--season",
    required=True, 
    type=int, help="Season (e.g. 2324)."
)
@click.option(
    "--date", "match_date",
    required=True,
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Match date (YYYY-MM-DD).",
)
@click.option("--home", required=True, type=str, help="Home team name.")
@click.option("--away", required=True, type=str, help="Away team name.")
@click.option("--score", required=True, type=str, help="Full-time score as H:A, (e.g. 2:1).")
@click.option("--half-time", required=True, type=str, help="Half-time score as H:A, (e.g. 1:0).")
def record(league, season, match_date, home, away, score, half_time):
    """Record the result of one match."""
    engine = db.get_engine()
    try:
        recording.record_match(engine, league, season, match_date, home, away, score, half_time)
    except Exception as e:
        raise click.ClickException(f"Failed to record this match: {e}")
    click.echo(f"Recorded: {home} {score} {away} ({match_date:%Y-%m-%d})")
