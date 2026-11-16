import sqlalchemy as sa

HOME_ADVANTAGE_SQL = """
SELECT
    COUNT(*) AS total,
    SUM(CASE WHEN m.fthg > m.ftag THEN 1 ELSE 0 END) AS home_wins,
    SUM(CASE WHEN m.fthg = m.ftag THEN 1 ELSE 0 END) AS draws,
    SUM(CASE WHEN m.fthg < m.ftag THEN 1 ELSE 0 END) AS away_wins
FROM match m
JOIN season s ON s.season_id = m.season_id
JOIN league l ON l.league_id = s.league_id
WHERE l.name = :league
    AND s.name = :season
"""


def get_home_advantage_percentage(engine, league, season):
    """Returns (home %, draw %, away %) for a league season."""
    with engine.connect() as conn:
        row = conn.execute(
            sa.text(HOME_ADVANTAGE_SQL),
            {"league": league, "season": str(season)}
        ).one()

    total_matches, home_wins, draws, away_wins = row

    if total_matches == 0:
        raise ValueError(f"No matches found for {league} {season}.")

    home_percentage = home_wins / total_matches * 100
    draw_percentage = draws / total_matches * 100
    away_percentage = away_wins / total_matches * 100

    return home_percentage, draw_percentage, away_percentage