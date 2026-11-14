CREATE TABLE IF NOT EXISTS league (
    league_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    CONSTRAINT league_name_key UNIQUE (name)
);

CREATE TABLE IF NOT EXISTS season (
    season_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    league_id INT NOT NULL,
    name TEXT NOT NULL,
    CONSTRAINT season_league_id_fkey FOREIGN KEY (league_id) REFERENCES league(league_id),
    CONSTRAINT season_league_id_name_key UNIQUE (league_id, name)
);

CREATE TABLE IF NOT EXISTS team (
    team_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    CONSTRAINT team_name_key UNIQUE (name)
);

CREATE TABLE IF NOT EXISTS match (
    match_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    season_id INT NOT NULL,
    match_date DATE NOT NULL,
    home_team_id INT NOT NULL,
    away_team_id INT NOT NULL,
    FTHG INT NOT NULL,
    FTAG INT NOT NULL,
    HTHG INT NOT NULL,
    HTAG INT NOT NULL,

    CONSTRAINT match_season_id_fkey FOREIGN KEY (season_id) REFERENCES season(season_id),
    CONSTRAINT match_home_team_id_fkey FOREIGN KEY (home_team_id) REFERENCES team(team_id),
    CONSTRAINT match_away_team_id_fkey FOREIGN KEY (away_team_id) REFERENCES team(team_id),

    CONSTRAINT match_season_date_home_key UNIQUE (season_id, match_date, home_team_id),
    CONSTRAINT match_season_date_away_key UNIQUE (season_id, match_date, away_team_id),

    CONSTRAINT match_teams_differ CHECK (home_team_id <> away_team_id),
    CONSTRAINT match_goals_not_negative CHECK (FTHG >= 0 AND FTAG >= 0),
    CONSTRAINT match_ht_goals_not_negative CHECK (HTHG >= 0 AND HTAG >= 0),
    CONSTRAINT match_ht_goals_not_above_ft_goals CHECK (HTHG <= FTHG AND HTAG <= FTAG)
);