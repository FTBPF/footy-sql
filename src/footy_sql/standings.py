import sqlalchemy as sa 

def get_standings(engine, league, season, as_of):
    """
    Returns a list of dictionaries with each team stats.
    """
    with engine.connect() as conn:
        season_id = conn.execute(
        sa.text("""
            SELECT s.season_id
            FROM season AS s
            JOIN league AS l
                ON l.league_id = s.league_id
            WHERE l.name = :league
                AND s.name = :season
        """),
            {"league": league, "season": season}
        ).scalar()

        if season_id is None:
            raise ValueError(
                f"Season '{season}' not found in league '{league}'."
            )

        return conn.execute(
            sa.text("""
                WITH team_matches AS (
                    SELECT
                        m.season_id,
                        m.match_date,
                        m.home_team_id AS team_id,
                        m.FTHG AS GF,
                        m.FTAG AS GA,
                        CASE
                            WHEN m.FTHG > m.FTAG THEN 'W'
                            WHEN m.FTHG = m.FTAG THEN 'D'
                            ELSE 'L'
                        END AS result
                    FROM match AS m
                    UNION ALL
                    SELECT
                        m.season_id,
                        m.match_date,
                        m.away_team_id AS team_id,
                        m.FTAG AS GF,
                        m.FTHG AS GA,
                        CASE
                            WHEN m.FTAG > m.FTHG THEN 'W'
                            WHEN m.FTAG = m.FTHG THEN 'D'
                            ELSE 'L'
                        END AS result
                    FROM match AS m
                ),
                team_stats AS (
                    SELECT
                        tm.team_id,
                        t.name AS team,
                        COUNT(*) AS P,
                        SUM(CASE WHEN tm.result = 'W' THEN 1 ELSE 0 END) AS W,
                        SUM(CASE WHEN tm.result = 'D' THEN 1 ELSE 0 END) AS D,
                        SUM(CASE WHEN tm.result = 'L' THEN 1 ELSE 0 END) AS L,
                        SUM(tm.GF) AS GF,
                        SUM(tm.GA) AS GA,
                        SUM(tm.GF) - SUM(tm.GA) AS GD,
                        SUM(
                            CASE
                                WHEN tm.result = 'W' THEN 3
                                WHEN tm.result = 'D' THEN 1
                                ELSE 0
                            END
                        ) AS Pts
                    FROM team_matches AS tm
                    JOIN team AS t ON t.team_id = tm.team_id
                    WHERE tm.season_id = :season_id
                      AND (
                          CAST(:as_of AS DATE) IS NULL
                          OR tm.match_date <= CAST(:as_of AS DATE)
                      )
                    GROUP BY tm.team_id, t.name
                )
                SELECT
                    RANK() OVER (
                        ORDER BY Pts DESC, GD DESC, GF DESC
                    ) AS "Pos",
                    team AS "Team",
                    P AS "P",
                    W AS "W",
                    D AS "D",
                    L AS "L",
                    GF AS "GF",
                    GA AS "GA",
                    GD AS "GD",
                    Pts AS "Pts"
                FROM team_stats
                ORDER BY "Pos", "Team"
            """),
            {
                "season_id": season_id,
                "as_of": as_of
            }
        ).mappings().all()
