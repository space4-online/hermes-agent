# Hermes Agent · MySQL DDL

This directory holds the **canonical, idempotent metadata-creation SQL** for
running Hermes Agent against an external MySQL service.  Every numbered file
is a Flyway-style migration that is applied at most once per target schema.

## Layout

```
sql/mysql/
├── state/                  state.db equivalent (sessions, messages, FTS, ...)
│   └── V1__init.sql
├── kanban/                 kanban.db equivalent (tasks, runs, events, ...)
│   └── V1__init.sql
├── memory_store/           holographic memory plugin (facts, entities, ...)
│   └── V1__init.sql
└── response_store/         OpenAI response chain cache
    └── V1__init.sql
```

Per-store files are versioned independently — `state` may sit at V3 while
`kanban` is still at V1.  The runner tracks each store's progress in its
own `schema_version` table (created automatically on first run).

## Naming convention

```
V<integer>__<short_description>.sql
```

* `<integer>` — strictly increasing per directory; gaps allowed.
* `<short_description>` — `[A-Za-z0-9_-]+`; `_` is rendered as a space in
  human-readable diagnostics.
* The body is plain MySQL DDL; multiple statements are separated by `;`
  on a top-level (not inside a string literal or comment).

The runner refuses to load files that don't match the pattern, so test
fixtures and ad-hoc scripts can sit alongside without interference.

## Applying

```bash
# Apply all pending migrations to every known store
python -m hermes_db.migrate

# Just one store
python -m hermes_db.migrate --store state

# See what would run without touching the DB
python -m hermes_db.migrate --status
python -m hermes_db.migrate --dry-run
```

Connection parameters come from `hermes_db.config.get_storage_config()`
which honours `storage:` in `config.yaml` plus `HERMES_DB_*` env vars
(see `docs/storage-mysql.md`).

## Authoring new migrations

1. Pick the next free number for the target store, e.g. `V2`.
2. Add `sql/mysql/<store>/V2__short_desc.sql`.  Keep DDL idempotent
   (`CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ... ADD COLUMN IF NOT
   EXISTS` is not portable to MySQL — use a guard query at the
   application layer if you need conditional alters, or rely on
   the file only running once).
3. Run `python -m hermes_db.migrate --status` against an empty DB and
   verify the new file appears in the **pending** list.
4. Run `python -m hermes_db.migrate` and verify the **applied** list
   then includes the new version.
5. Avoid editing already-applied migrations — the runner records a
   sha256 checksum of every file and warns on drift.  If a fix is
   absolutely required, add a follow-up `V<N+1>__fix_xxx.sql` instead.

## Engine + charset notes

All tables are `ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC`.

* `DYNAMIC` row format keeps long `LONGTEXT` columns out-of-page so the
  primary B-tree stays compact.  Required when a table has multiple
  large text columns (e.g. `messages.content`, `messages.tool_calls`).
* `utf8mb4` is required for emoji / 4-byte CJK / supplementary planes;
  the legacy `utf8` (3-byte) charset would silently truncate.

Full-text search uses MySQL's built-in `FULLTEXT ... WITH PARSER ngram`
so CJK substring queries match without external add-ons.  The minimum
ngram token size is governed by the server-wide
`ngram_token_size` (default 2); 2 is fine for our use cases.  If your
DBA tightened it, set it back at the session level via your driver's
`init_command` or change `mysqld.cnf`.

## Mapping notes vs SQLite

| SQLite construct | MySQL equivalent |
|---|---|
| `INTEGER PRIMARY KEY AUTOINCREMENT` | `BIGINT AUTO_INCREMENT PRIMARY KEY` |
| `REAL` | `DOUBLE` |
| `TEXT` (small) | `VARCHAR(N)` |
| `TEXT` (large / unbounded) | `LONGTEXT` |
| `BLOB` | `LONGBLOB` |
| `CREATE VIRTUAL TABLE ... fts5` | `FULLTEXT KEY ... WITH PARSER ngram` |
| `messages MATCH ?` | `MATCH(messages.content) AGAINST(? IN BOOLEAN MODE)` |
| `CREATE TRIGGER ... fts insert/delete/update` | not needed (in-place FT index) |
| `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` | `DATETIME DEFAULT CURRENT_TIMESTAMP` |

The translation logic lives in `hermes_db.dialect`; call sites that
need to branch on engine (e.g. FTS query construction) should always
go through it instead of inlining `if conn.backend == "mysql"`.

## Bootstrapping a fresh MySQL service

```sql
-- Run once as a privileged user.
CREATE DATABASE hermes
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER 'hermes'@'%' IDENTIFIED BY '<replace-me>';
GRANT ALL PRIVILEGES ON hermes.* TO 'hermes'@'%';
FLUSH PRIVILEGES;
```

If you prefer one database per store (set
`storage.mysql.per_store_database` in `config.yaml`), repeat the
`CREATE DATABASE` step for each.  The migration runner does NOT create
databases — that's an ops decision.
