import pandas as pd
import sqlalchemy as sa
import pathlib

THIS_DIR = pathlib.Path(__file__).parent
DATA_DIR = THIS_DIR.parent.parent / "data"

def load_season_csv(engine, league, season, data_dir=DATA_DIR):
    """Returns the number of matches and the number of teams loaded."""

    all_matches_df = read_file(league, season, data_dir)

    teams_list = list(
        set(
            all_matches_df["HomeTeam"].to_list() +
            all_matches_df["AwayTeam"].to_list()
        )
    )

    with engine.begin() as conn:
        league_id = insert_league(conn, league)

        season_id = insert_season(conn, league_id, season)

        team_map = insert_teams(conn, teams_list)

        match_dicts = get_match_dicts(all_matches_df, season_id, team_map)

        delete_previous_matches(conn, season_id)

        insert_matches(conn, match_dicts)

    return len(match_dicts), len(teams_list)


def read_file(league, season, data_dir):
    if league == "league":
        filename = data_dir.parent / "fixtures" / f"{league}-{season}.csv"
    else:
        filename = data_dir / f"{league}-{season}.csv"

    try:
        return pd.read_csv(filename, parse_dates=["Date"], dayfirst=True)
    except FileNotFoundError:
        raise ValueError(f"File not found: {filename}")


def insert_league(conn, league):
    conn.execute(
        sa.text("INSERT INTO league (name) VALUES (:name) "
                "ON CONFLICT (name) DO NOTHING"
        ),
        {"name": league}
    )    
    return conn.execute(
        sa.text("SELECT league_id FROM league WHERE name = :name"),
        {"name": league}
    ).scalar()
    


def insert_season(conn, league_id, season):
    conn.execute(
        sa.text(
            "INSERT INTO season (league_id, name) VALUES (:league_id, :name) "
            "ON CONFLICT (league_id, name) DO NOTHING"
        ),
        {"league_id": league_id, "name": season}
    )
    return conn.execute(
        sa.text("SELECT season_id FROM season WHERE league_id = :league_id AND name = :name"),
        {"league_id": league_id, "name": season}
    ).scalar()


def insert_teams(conn, teams_list):
    """Insere as equipas e devolve o dicionário nome da equipa: team_id."""
    team_dicts = [{"name": team} for team in teams_list]
    conn.execute(
        sa.text("INSERT INTO team (name) VALUES (:name) ON CONFLICT (name) DO NOTHING"),
        team_dicts
    )
    team_rows = conn.execute(sa.text("SELECT team_id, name FROM team")).mappings().all()
    return {row["name"]: row["team_id"] for row in team_rows}


def get_match_dicts(all_matches_df, season_id, team_map):
    match_dicts = []
    for _, row in all_matches_df.iterrows():
        match_dicts.append({
            "season_id": season_id,
            "match_date": row['Date'].strftime('%Y-%m-%d'),
            "home_team_id": team_map[row['HomeTeam']],
            "away_team_id": team_map[row['AwayTeam']],
            "fthg": int(row['FTHG']),
            "ftag": int(row['FTAG']),
            "hthg": int(row['HTHG']),
            "htag": int(row['HTAG']),
        })
    return match_dicts


def insert_matches(conn, match_dicts):
    """Insere as partidas na tabela match."""
    if match_dicts:
        conn.execute(
            sa.text(
                """
                INSERT INTO match (season_id, match_date, home_team_id, away_team_id, FTHG, FTAG, HTHG, HTAG)
                VALUES (:season_id, :match_date, :home_team_id, :away_team_id, :fthg, :ftag, :hthg, :htag)
                """
            ),
            match_dicts
        )


def delete_previous_matches(conn, season_id):
    """Remove os jogos anteriores da season."""
    conn.execute(
        sa.text("DELETE FROM match WHERE season_id = :season_id"),
        {"season_id": season_id}
    )
