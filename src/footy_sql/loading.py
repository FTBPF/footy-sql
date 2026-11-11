import pandas as pd
import sqlalchemy as sa
import pathlib

THIS_DIR = pathlib.Path(__file__).parent
DATA_DIR = THIS_DIR.parent.parent / "data"

def load_season_csv(engine, league, season, data_dir=DATA_DIR):
    """Returns the number of matches and the number of teams loaded."""

    all_matches_df = read_file(league, season, data_dir)
    check_columns(all_matches_df)
    fix_types(all_matches_df)

    teams_list = list( set( all_matches_df["HomeTeam"].to_list() + all_matches_df["AwayTeam"].to_list() ) )

    with engine.begin() as conn:
        # Inserir a liga
        conn.execute(
            sa.text("INSERT INTO league (name) VALUES (:name) "
                    "ON CONFLICT (name) DO NOTHING"
            ),
            {"name": league}
        )
        league_id = conn.execute(
            sa.text("SELECT league_id FROM league WHERE name = :name"),
            {"name": league}
        ).scalar()

        # Inserir a season
        conn.execute(
            sa.text(
                "INSERT INTO season (league_id, name) VALUES (:league_id, :name) "
                "ON CONFLICT (league_id, name) DO NOTHING"
            ),
            {"league_id": league_id, "name": season}
        )
        season_id = conn.execute(
            sa.text("SELECT season_id FROM season WHERE league_id = :league_id AND name = :name"),
            {"league_id": league_id, "name": season}
        ).scalar()

        # Remover jogos anteriores
        conn.execute(
            sa.text("DELETE FROM match WHERE season_id = :season_id"),
            {"season_id": season_id}
        )

        # Inserir as equipas
        team_dicts = [{"name": team} for team in teams_list]
        conn.execute(
            sa.text("INSERT INTO team (name) VALUES (:name) ON CONFLICT (name) DO NOTHING"),
            team_dicts
        )

        # Dicionário nome da equipa: team_id
        team_rows = conn.execute(sa.text("SELECT team_id, name FROM team")).mappings().all()
        team_map = {row["name"]: row["team_id"] for row in team_rows}

        # Lista de dicionários de cada partida
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

        # Inserir as partidas na tabela match
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

    return len(match_dicts), len(teams_list)


def read_file(league, season, data_dir):
    if league == "league":
        filename = data_dir.parent / "fixtures" / f"{league}-{season}.csv"
    else:
        filename = data_dir / f"{league}-{season}.csv"

    try:
        return pd.read_csv(filename)
    except FileNotFoundError:
        raise ValueError(f"File not found: {filename}")


def check_columns(all_matches_df):
    needed_columns = [
        "Date",
        "HomeTeam",
        "AwayTeam",
        "FTHG",
        "FTAG",
        "HTHG",
        "HTAG",
    ]
    missing_columns = [
        column for column in needed_columns if column not in all_matches_df.columns
    ]
    if missing_columns:
        raise ValueError(f"Missing columns: {missing_columns}.")


def fix_types(all_matches_df):
    try:
        all_matches_df["Date"] = pd.to_datetime(
            all_matches_df["Date"], format="mixed", dayfirst=True
        )
        all_matches_df["FTHG"] = all_matches_df["FTHG"].astype(int)
        all_matches_df["FTAG"] = all_matches_df["FTAG"].astype(int)
        all_matches_df["HTHG"] = all_matches_df["HTHG"].astype(int)
        all_matches_df["HTAG"] = all_matches_df["HTAG"].astype(int)
    except ValueError as e:
        raise ValueError(f"Invalid values in Date, FTHG or FTAG: {e}")
