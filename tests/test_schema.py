import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError


def test_unique_team_name(test_engine):
    """Duas equipas com o mesmo nome devem ser rejeitadas."""
    with test_engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO team (name) VALUES ('Porto')"))

        with pytest.raises(IntegrityError) as exc_info:
            conn.execute(sa.text("INSERT INTO team (name) VALUES ('Porto')"))
        assert "team_name_key" in str(exc_info.value)


def test_match_teams_differ(test_engine):
    """Uma equipa a jogar contra si própria deve ser rejeitada."""
    with test_engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO league (name) VALUES ('Liga')"))
        conn.execute(sa.text("INSERT INTO season (league_id, name) VALUES (1, '2023-24')"))
        conn.execute(sa.text("INSERT INTO team (name) VALUES ('Benfica')"))
        
        with pytest.raises(IntegrityError) as exc_info:
            conn.execute(sa.text(
                "INSERT INTO match (season_id, match_date, home_team_id, away_team_id, FTHG, FTAG, HTHG, HTAG) "
                "VALUES (1, '2023-08-20', 1, 1, 1, 1, 0, 0)"
            ))
        assert "match_teams_differ" in str(exc_info.value)


def test_negative_goals_rejected(test_engine):
    """Golos negativos devem ser rejeitados pela base de dados."""
    with test_engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO league (name) VALUES ('Liga')"))
        conn.execute(sa.text("INSERT INTO season (league_id, name) VALUES (1, '2023-24')"))
        conn.execute(sa.text("INSERT INTO team (name) VALUES ('Sporting')"))
        conn.execute(sa.text("INSERT INTO team (name) VALUES ('Braga')"))
        
        with pytest.raises(IntegrityError) as exc_info:
            conn.execute(sa.text(
                "INSERT INTO match (season_id, match_date, home_team_id, away_team_id, FTHG, FTAG, HTHG, HTAG) "
                "VALUES (1, '2023-08-20', 1, 2, -1, 0, 0, 0)"
            ))
        assert "match_goals_not_negative" in str(exc_info.value)


def test_duplicate_home_match_same_day(test_engine):
    """Dois jogos com a mesma equipa da casa no mesmo dia na mesma época devem ser rejeitados."""
    with test_engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO league (name) VALUES ('Liga')"))
        conn.execute(sa.text("INSERT INTO season (league_id, name) VALUES (1, '2023-24')"))
        conn.execute(sa.text("INSERT INTO team (name) VALUES ('Porto')"))
        conn.execute(sa.text("INSERT INTO team (name) VALUES ('Sporting')"))
        conn.execute(sa.text("INSERT INTO team (name) VALUES ('Benfica')"))
        
        # Primeiro jogo (Porto vs Sporting - IDs 1 e 2)
        conn.execute(sa.text(
            "INSERT INTO match (season_id, match_date, home_team_id, away_team_id, FTHG, FTAG, HTHG, HTAG) "
            "VALUES (1, '2023-08-20', 1, 2, 1, 0, 0, 0)"
        ))
        
        # Segundo jogo (Porto vs Benfica - IDs 1 e 3)
        with pytest.raises(IntegrityError) as exc_info:
            conn.execute(sa.text(
                "INSERT INTO match (season_id, match_date, home_team_id, away_team_id, FTHG, FTAG, HTHG, HTAG) "
                "VALUES (1, '2023-08-20', 1, 3, 2, 2, 1, 1)"
            ))
        assert "match_season_date_home_key" in str(exc_info.value)

