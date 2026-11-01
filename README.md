# Footy SQL

Rebuild `footy-table` on a PostgreSQL backend: the same league tables, now
computed by a database you designed, loaded safely, and kept correct when
results are recorded one at a time.

You already know the rules, the data and the expected answers: your pandas
`footy-table` is the reference implementation. This week is about the
database underneath.


## Learning Objectives

* Designing a normalized schema for a domain you know, with keys, types and
  constraints that make bad data impossible to store (Session 4).
* Loading CSV data into that schema from Python, inside transactions,
  idempotently (Sessions 4 and 5).
* Moving computation into SQL: the league table as a query, with
  aggregation, `CASE`, CTEs and window functions (Sessions 2 and 3).
* Parameterized queries from Python, never f-strings (Session 5).
* Reading query plans and adding the indexes your queries actually need
  (Session 5).
* Testing database code with `pytest` against a real PostgreSQL, locally
  and in GitHub Actions.


## Concepts

Same as `footy-table` (**Match**, **Season**, **League**, **Table**, and
its `P`/`W`/`D`/`L`/`GF`/`GA`/`GD`/`Pts` columns), plus:

* **Schema** — the PostgreSQL tables, constraints and views `footy` owns,
  created by `footy db init`.
* **Load** — reading one `{league}-{season}.csv` file into the schema. A
  load is all or nothing, and loading the same file twice changes nothing.
* **Record** — adding a single match result through the CLI, the way a
  league secretary would on match day.


## Data Source

The same football-data.co.uk CSV files as `footy-table`: copy its `data/`
directory (the `P1` and `SP1` seasons, plus `notes.txt`). No networking:
everything works from local files.

The two hand-verified fixtures from `footy-table`'s Acceptance are in this
directory's `fixtures/`: `league-p.csv` and `league-y.csv`.

Two databases on the lab VM are yours, already created and empty:

* `ff.footy-sql`, for development: what `footy` uses day to day.
* `ff.footy-sql-test`, for the tests (see Guidance). Tests never touch the
  development database.

Their names work as they are in `psql -d ...` and in SQLAlchemy URLs;
inside SQL they need double quotes (`"ff.footy-sql"`), because of the dot
and the hyphen.

Connect as in the sessions, with the libpq environment variables
(`PGHOST`, `PGUSER`, `PGPASSWORD`, ...), and point `PGDATABASE` at the
development database:

```
export PGDATABASE=ff.footy-sql
```

With those set, `psql` needs no connection options, and neither does
`footy` (see below).


## Usage and Behaviour

`footy` is still a CLI structured like `git`. It connects to the database
in the `FOOTY_DB_URL` environment variable, a SQLAlchemy URL. When that's
not set, it uses `postgresql+psycopg://`: an otherwise empty URL, which
libpq fills in from the `PG*` variables, as it does for `psql`. Day to
day, `PGDATABASE=ff.footy-sql` is all you need; `FOOTY_DB_URL` is for
pointing `footy` somewhere else (the tests do). If the database can't be
reached, fail with a clear message, not a traceback.


### Schema

```
footy db init [--drop]
```

* Creates the schema: tables, constraints, indexes and views. Running it
  on a database that already has the schema does nothing (and says so).
* `--drop` drops everything `footy` owns first, after asking for
  confirmation (`click.confirm`).
* Design it yourself (see **Designing the Schema**, below). It must, at
  least, make these impossible:
  * Two teams with the same name.
  * A match between a team and itself.
  * Negative goals, or half-time goals greater than full-time goals.
  * Two matches with the same home team on the same day in the same
    season.
  * A match whose teams, league or season don't exist.
* Keep the DDL in a `.sql` file inside the package, read and run by
  `footy db init`.

**DDL** (Data Definition Language, Session 4) is the part of SQL that
defines a database's *structure*: `CREATE TABLE`, `ALTER TABLE`,
`DROP TABLE`, `CREATE INDEX`, `CREATE VIEW`, and the constraints inside
them. The rest, `SELECT`, `INSERT`, `UPDATE` and `DELETE`, works on the
*data* in that structure. Your `schema.sql` is DDL only: running it gives
you empty tables, ready to load.


### Designing the Schema

You've designed DataFrames, not databases, so take this step slowly: it's
the one that's expensive to get wrong later. A reminder of Session 4's
principles:

* **One table per concept.** Each kind of thing the domain talks about
  gets its own table, and each row is exactly one of those things.
* **Store each fact once.** If a value would repeat across many rows (a
  team's name, in every one of its matches), it's a concept of its own:
  give it a table, and refer to it by key. Renaming a team then changes
  one row, not hundreds.
* **Every table has a primary key.** A surrogate one (an
  `integer GENERATED ALWAYS AS IDENTITY` column) or a natural one (a value
  that identifies the row and never changes). With a surrogate key, add a
  `UNIQUE` constraint on whatever identifies the row in the real world.
* **Every "belongs to" is a foreign key.** If a row refers to a row in
  another table, a `FOREIGN KEY` makes sure that row exists.
* **Types say what's allowed.** `date` for dates, `integer` (or
  `smallint`) for goals, `text` for names: not everything as `text`.
* **Every rule is a constraint.** `NOT NULL` for what must be there,
  `UNIQUE` for what can't repeat, `CHECK` for what must hold within a row,
  `FOREIGN KEY` for what must exist elsewhere. Name them
  (`CONSTRAINT some_name CHECK (...)`): you'll map those names to error
  messages in `footy record`.

Your schema needs, at least, these four entities: **league**, **season**,
**team** and **match**. Their columns, keys, types and constraints are up
to you. Questions to answer on paper before writing any DDL:

* What identifies a league? And a season: is `2023-24` (or `fixture`)
  unique on its own, or only within a league?
* Does a team belong to a league, or only to the matches it plays?
* What identifies a match in the real world? (One of the rules above
  answers this.)
* Which CSV columns do you need to store, and which can be computed from
  others? (`FTR` and `HTR`, say.)
* When `footy load` re-loads a season, which rows does it delete or
  replace, and in what order, given the foreign keys?

Self-check, once your ER diagram is drawn:

* Every rule under **Schema** maps to a named constraint, and you can say
  which.
* No team name is stored more than once, anywhere.
* Every table has a primary key; every reference to another table is a
  foreign key.
* You can write, on paper, a query for one team's matches in one season.

Then send your mentor a photo of the diagram, and carry on: don't wait for
an answer. The next check-in confirms the design, or asks for changes
while they're still cheap.


### Loading

```
footy load --league {league} --season {season}
```

* Reads `data/{league}-{season}.csv` (same resolution and error rules as
  `footy-table`) and loads it, in a single transaction: if any row fails,
  nothing is loaded.
* Idempotent: loading a season that's already there replaces it (or
  skips it: your call, documented), but never duplicates matches.
* Prints a one-line summary:

  ```
  $ footy load --league p --season fixture
  Loaded p/fixture: 6 matches, 4 teams.
  ```


### League Table

```
footy table --league {league} --season {season} [--as-of {YYYY-MM-DD}]
```

* Same output and sort order as `footy-table` (points, then goal
  difference, then goals for), plus a `Pos` column computed in SQL with a
  window function.
* The whole table is computed by **one SQL query** (or a view plus one
  query), run with parameters. Python only formats the result.


### Recording a Result

```
footy record --league {league} --season {season} --date {YYYY-MM-DD} \
             --home {team} --away {team} --score {H:A} [--half-time {H:A}]
```

* Scores are home and away goals separated by a colon (`--score 2:1`).
  `str.partition(':')` is all the parsing you need.
* Adds one match, in a transaction. Unknown teams, a duplicate match, or
  a score the schema rejects end with a clear, specific message that
  names the problem (map the database's constraint errors to your own
  messages: see Guidance).


### Home Advantage

```
footy home-advantage --league {league} --season {season}
```

* Same output as `footy-table`'s, computed in SQL.


### Explain

```
footy explain table --league {league} --season {season}
```

* Prints the PostgreSQL plan (`EXPLAIN ANALYZE`) of the `table` query.
  Use it to justify the indexes in your schema.


## Guidance

* Initialize with `uv init --app --package footy-sql` (the command is still
  `footy`), and add every dependency up front:

  ```
  uv add click sqlalchemy "psycopg[binary]" pandas pyarrow duckdb
  uv add --dev pytest
  ```

  `pandas` is only for pretty-printing and, in the stretch goals, Parquet
  export (with `pyarrow`): every computation is SQL. `duckdb` is for the
  stretch goals, too.
* Suggested module layout:
  * `__init__.py` — CLI entry point; calls into other modules, nothing else.
  * `db.py` — the engine from `FOOTY_DB_URL`, a small `query` helper, and
    `init_schema`.
  * `schema.sql` — the DDL.
  * `loading.py` — CSV parsing (dates, scores) and the load transaction.
  * `standings.py`, `stats.py` — the SQL for the table and home advantage,
    and functions that run it.
  * `record.py` — recording one result, with error mapping.
* **Develop SQL by hand first**, then move it into Python. Use `psql` or
  DBeaver, whichever suits the moment: `psql` has `\dt`, `\d match`,
  `\i schema.sql` and `\timing`; DBeaver has the ER diagram, result grids
  and comfortable editing. Run your DDL, try the inserts that must fail,
  build the table query step by step: Python only runs SQL you've already
  seen working.
* The `query` helper is Session 6's B.3 without pandas: it returns rows
  that you can index by column name.

  ```python
  import sqlalchemy as sa

  def query(engine, sql, **params):
      """Run `sql`, with its `:name` parameters, and return the rows."""
      with engine.connect() as conn:
          return conn.execute(sa.text(sql), params).mappings().all()

  rows = query(engine, 'SELECT name FROM team WHERE name LIKE :prefix', prefix='A%')
  rows[0]['name']
  ```

* Every value that reaches SQL goes through a parameter. Grep your code
  for `f"SELECT` before each PR.
* **Transactions from Python.** `engine.begin()` opens a connection and a
  transaction. Leaving the `with` block normally commits; an exception
  inside it (from SQL or from your own code) rolls *everything* back, and
  carries on. An example, nothing to do with football: a bank transfer,
  where a `transfer` table logs every transfer, with foreign keys to
  `account`.

  ```python
  import sqlalchemy as sa

  def transfer(engine, src, dst, amount):
      params = {'src': src, 'dst': dst, 'amount': amount}
      with engine.begin() as conn:  # BEGIN
          conn.execute(sa.text(
              'UPDATE account SET balance = balance - :amount WHERE id = :src'
          ), params)
          conn.execute(sa.text(
              'UPDATE account SET balance = balance + :amount WHERE id = :dst'
          ), params)
          conn.execute(sa.text(
              'INSERT INTO transfer (src, dst, amount) VALUES (:src, :dst, :amount)'
          ), params)
      # COMMIT, if we got here.
  ```

  If `dst` doesn't exist, the second `UPDATE` changes no rows, but the
  `INSERT` breaks the foreign key on `transfer.dst` and raises: the
  whole block rolls back, and the money taken from `src` is back where it
  was. Two more things you'll need:
  * `conn.execute(statement, list_of_dicts)` runs the statement once per
    dict, in the same transaction: handy for loading a season's matches.
  * Call your loading and recording functions from inside one
    `engine.begin()` block, not one per statement: that's what makes the
    whole load all or nothing.
* **Turning constraint errors into messages.** A broken constraint raises
  `sqlalchemy.exc.IntegrityError`; its `.orig.diag.constraint_name` is the
  name you gave the constraint in your DDL. Map names to messages:

  ```python
  import click
  from sqlalchemy.exc import IntegrityError

  MESSAGES = {
      'balance_not_negative': 'Not enough money in the source account.',
      'transfer_dst_fkey': 'The destination account does not exist.',
  }

  try:
      transfer(engine, src=1, dst=99, amount=50)
  except IntegrityError as e:
      name = e.orig.diag.constraint_name
      raise click.ClickException(MESSAGES.get(name, str(e.orig)))
  ```

* **Testing against PostgreSQL.** Tests need a real database:
  * Locally: `ff.footy-sql-test` on the VM, in a `FOOTY_TEST_DB_URL`
    environment variable. The same `PG*` variables, another database:
    `postgresql+psycopg:///ff.footy-sql-test` (three slashes: no host,
    so libpq takes it from `PGHOST`, then the database name, which wins
    over `PGDATABASE`). Never point tests at `ff.footy-sql`: if
    `FOOTY_TEST_DB_URL` isn't set, the tests should stop, not fall back
    to the default.
  * A `pytest` fixture that drops and re-creates the schema at the start of
    each test session, and empties every table before each test
    (`TRUNCATE ... RESTART IDENTITY CASCADE`), so tests never see each
    other's data.
  * In GitHub Actions: a throwaway PostgreSQL in a `services:` container,
    with the same tests. The relevant part of the workflow:

    ```yaml
    jobs:
      test:
        runs-on: ubuntu-latest
        services:
          postgres:
            image: postgres:17
            env:
              POSTGRES_USER: footy
              POSTGRES_PASSWORD: footy
              POSTGRES_DB: footy_test
            ports: ['5432:5432']
            options: >-
              --health-cmd pg_isready --health-interval 5s
              --health-timeout 5s --health-retries 10
        env:
          FOOTY_TEST_DB_URL: postgresql+psycopg://footy:footy@localhost:5432/footy_test
        steps:
          # checkout, set up uv, uv run pytest
    ```

### Possible course

1. Schema on paper (through the self-check), then `schema.sql`, run and
   tried by hand, then `footy db init`, with a test that every rule under
   **Schema** is enforced (each as an expected `IntegrityError`).
2. Loading the fixture, then real seasons.
3. The table query: first by hand, then in `standings.py`, then the CLI.
4. `record`, with its error messages; `home-advantage`.
5. `explain`, indexes, and polish.


## Suggested Pace

One working week, at 4-6h a day. Every row is one or more branches, PRs
with green GitHub Actions, and merges. Check-ins happen about twice a week,
on days that vary: whenever one comes, show where you are, and never wait
for one to carry on.

| Day | Focus | End of day |
|-----|-------|------------|
| 1 | **Schema.** ER diagram on paper, through **Designing the Schema**'s questions and self-check; photo sent to your mentor. Then `schema.sql`, run by hand, with the inserts that must fail. Then `footy db init` (idempotent, `--drop` with confirmation), the `pytest` fixture against `FOOTY_TEST_DB_URL`, and the GitHub Actions PostgreSQL service. One test per rule in **Schema**. | CI green, running against a real PostgreSQL; every rule proven by a failing insert. |
| 2 | **Loading.** Parse the CSV (dates in two formats, scores as integers), load it in one transaction, idempotently. Tests: the fixture loads 6 matches and 4 teams; loading twice changes nothing; a malformed row loads nothing. Then load the real `P1` and `SP1` seasons. | `footy load` works on fixtures and real data. |
| 3 | **The table, in SQL.** Write the query by hand first: one row per team per match (a `UNION ALL` of home and away), then aggregate, then `RANK()` for `Pos`. Move it into `standings.py`, with `--as-of` as a parameter. Test against Acceptance. | `footy table` prints the Acceptance standings, for the full season and `--as-of`. |
| 4 | **Record and home advantage.** `footy record` with clear errors for each constraint, tested. `footy home-advantage` in SQL. Compare every real-season table with your pandas `footy-table`'s output. | Both commands tested; SQL and pandas tables match on real data. |
| 5 | **Explain, indexes, slack.** `footy explain table`, then indexes justified by its plans (before/after in your PR description). README: setup (the `PG*` variables, `FOOTY_DB_URL`), the schema diagram. Catch up; stretch goals only after that. | Ready for the final review at the next check-in: walk through the schema, one plan, and one test. |


## Acceptance

**league-p.csv** (in `fixtures/`), loaded as league `p`, season `fixture`:

* `footy load` reports 6 matches and 4 teams.
* Full-season table (Pos, Team, P, W, D, L, GF, GA, GD, Pts):
  * 1, Comets — 3, 3, 0, 0, 6, 2, +4, **9**
  * 2, Badgers — 3, 1, 1, 1, 4, 3, +1, **4**
  * 3, Anchors — 3, 0, 2, 1, 2, 4, −2, **2**
  * 4, Drifters — 3, 0, 1, 2, 2, 5, −3, **1**
* `--as-of 2023-08-22` (first four matches):
  * 1, Comets — 2, 2, 0, 0, 4, 1, +3, **6**
  * 2, Badgers — 2, 1, 1, 0, 3, 1, +2, **4**
  * 3, Anchors — 2, 0, 1, 1, 1, 3, −2, **1**
  * 4, Drifters — 2, 0, 0, 2, 1, 4, −3, **0**
* Home advantage: 2 home wins, 2 draws, 2 away wins (33.3% each).

**league-y.csv**, as league `y`, season `fixture`: 3 matches, 14 goals.

**Database behaviour**, each covered by a test:

* Loading `league-p.csv` twice leaves exactly 6 matches.
* A CSV with one malformed row (say, `FTHG` = `x`) loads nothing at all.
* `footy record ... --home Anchors --away Anchors ...` is rejected with a
  message about a team playing itself.
* `footy record ... --score -1:0` is rejected (by the database, not only
  by your Python code: test the constraint directly, too).
* Recording a match that already exists is rejected with a clear message.
* Recording a valid new match for league `p` changes the table: e.g.
  `--date 2023-09-12 --home Drifters --away Comets --score 3:0` gives
  Drifters 4 points, and Comets a goal difference of +1.

**Real data:** every `P1` and `SP1` season's final table matches your pandas
`footy-table` output, row for row.


## Stretch Goals

* `footy history --team {team}`: every match of a team in a season, with a
  running points total (a window function).
* A materialized view for the table, refreshed by `load` and `record`.
  Measure whether it's worth it.
* `footy export --league --season` writing the season to Parquet; query it
  with DuckDB and compare with PostgreSQL (Session 6's head to head, on
  your own data). Two ways to write the file, pick one:
  * pandas: `pd.read_sql_query(sa.text(sql), conn, params=...)`, then
    `.to_parquet(path)` (which uses `pyarrow`).
  * DuckDB, attached to PostgreSQL: `INSTALL postgres; LOAD postgres;`,
    then `ATTACH '<libpq connection string>' AS pg (TYPE postgres)`, then
    `COPY (SELECT ... FROM pg.public.match ...) TO 'season.parquet'`.


## Parting Principles

* Same Git and GitHub workflow as always: a branch per "thing", small
  commits, a PR, green Actions, merge, clean up.
* The database is part of your code: its schema lives in the repository,
  is created by your tool, and is tested like everything else.
* If a rule matters, enforce it in the database. Python checks give nicer
  messages; constraints give guarantees.
