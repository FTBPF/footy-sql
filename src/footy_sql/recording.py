import sqlalchemy as sa


def parse_score(score, option):
    """Parse a score like '2:1' into two integers."""
    try:
        home, away = map(int, score.split(":"))
        if home < 0 or away < 0:
            raise ValueError
        return home, away
    except ValueError:
        raise ValueError(f"{option} must look like H:A (example: 2:1).")


def record_match(engine, league, season, match_date, home, away, score, half_time):
    """Record a match in the database."""

    fthg, ftag = parse_score(score, "--score")
    hthg, htag = parse_score(half_time, "--half-time")

    with engine.begin() as conn:
        season_id = conn.execute(
            sa.text("""
                SELECT s.season_id
                FROM season s
                JOIN league l ON l.league_id = s.league_id
                WHERE l.name = :league AND s.name = :season
            """),
            {"league": league, "season": str(season)}
        ).scalar()

        if season_id is None:
            raise ValueError(f"No season {season} found for league {league}.")

        teams = conn.execute(
            sa.text("""
                SELECT team_id, name
                FROM team
                WHERE name IN (:home, :away)
            """),
            {"home": home, "away": away}
        ).mappings().all()

        team_ids = {team["name"]: team["team_id"] for team in teams}

        if home not in team_ids or away not in team_ids:
            raise ValueError(f"Unknown team: {home}")

        conn.execute(
            sa.text("""
                INSERT INTO match (season_id, match_date, home_team_id, away_team_id, FTHG, FTAG, HTHG, HTAG)
                VALUES (:season_id, :match_date, :home_id, :away_id, :fthg, :ftag, :hthg, :htag)
            """),
            {
                "season_id": season_id,
                "match_date": match_date,
                "home_id": team_ids[home],
                "away_id": team_ids[away],
                "fthg": fthg,
                "ftag": ftag,
                "hthg": hthg,
                "htag": htag,
            }
        )
