# MySQL Storage Backend

> Status: **partial** (feature/mysql-backend branch).
> SQLite remains the default; MySQL is opt-in.

Hermes Agent normally keeps four SQLite files under `$HERMES_HOME`:

| Logical store     | SQLite file              | Purpose                                  |
|-------------------|--------------------------|------------------------------------------|
| `state`           | `state.db`               | sessions, messages, telemetry meta       |
| `kanban`          | `kanban.db` (per board)  | tasks, runs, events, notify subs         |
| `memory_store`    | `memory_store.db`        | holographic facts + entities + HRR banks |
| `response_store`  | `response_store.db`      | OpenAI Responses API LRU cache           |

The MySQL backend lets a single, externally managed MySQL service host all
four stores. This makes Hermes Agent itself stateless on disk so a host
swap (container restart, DR failover, machine migration) becomes a config
flip rather than a file copy.

## Quickstart

1. Install the extra:

   ```bash
   pip install 'hermes-agent[mysql]'
   ```

2. Provision the schemas. We ship the DDL as Flyway-style files under
   `sql/mysql/<store>/V*__*.sql`. The bundled migrator runs them in
   order and records what it applied in a `schema_version` table:

   ```bash
   # Status report (no writes)
   python -m hermes_db.migrate --backend mysql --store state          --status
   python -m hermes_db.migrate --backend mysql --store kanban         --status
   python -m hermes_db.migrate --backend mysql --store memory_store   --status
   python -m hermes_db.migrate --backend mysql --store response_store --status

   # Apply
   python -m hermes_db.migrate --backend mysql --store state
   # ... repeat per store
   ```

3. Switch the backend. Either edit `~/.hermes/cli-config.yaml`:

   ```yaml
   storage:
     backend: mysql
     mysql:
       host: db.internal
       port: 3306
       user: hermes
       password: ${MYSQL_PASSWORD}
       database: hermes          # all stores share this DB by default
       charset: utf8mb4
       # Or split: per_store_database: {state: hermes_state, ...}
   ```

   …or set environment overrides (highest precedence):

   ```bash
   export HERMES_DB_BACKEND=mysql
   export HERMES_DB_HOST=db.internal
   export HERMES_DB_USER=hermes
   export HERMES_DB_PASSWORD=...
   export HERMES_DB_NAME=hermes
   ```

## What works today

| Store            | MySQL status   | Notes                                              |
|------------------|----------------|----------------------------------------------------|
| `response_store` | ✅ implemented | LRU cache + conversation index, full upsert path. |
| `memory_store`   | ✅ implemented | Holographic facts; FTS5 → FULLTEXT WITH PARSER ngram; LONGTEXT dedup via `content_hash` (sha256). |
| `state`          | ⚠️ guarded     | DDL ready, code rewrite pending. Booting `SessionDB` against MySQL raises a clear error. |
| `kanban`         | ⚠️ guarded     | DDL ready (single-DB multi-tenant via `board_slug` column), code rewrite pending. |

The "guarded" stores will fall over loudly the moment something tries to
open them on MySQL — there is no silent fallback to SQLite. Either:

* keep `storage.backend = sqlite` (default), or
* wait for the follow-up that rewrites SessionDB / kanban_db SQL to inject
  `board_slug` and switch to dialect-aware syntax.

## Schema layout

Every DDL change is a new file under
`sql/mysql/<store>/V<N>__<description>.sql`. The migrator:

* runs them in numeric order,
* records sha256 in `schema_version` so manual edits trigger a warning,
* refuses to re-run a script whose checksum drifted (so accidental edits
  do not silently ship).

Notable structural differences vs SQLite:

* `INTEGER PRIMARY KEY AUTOINCREMENT` → `BIGINT AUTO_INCREMENT PRIMARY KEY`.
* SQLite FTS5 virtual tables → `FULLTEXT(...) WITH PARSER ngram` indexes
  on the parent table. CJK queries work because `ngram` is byte-based.
* `TEXT UNIQUE` over potentially-long values → `LONGTEXT` + a sister
  `content_hash CHAR(64) UNIQUE` populated by the application.
* `INSERT OR REPLACE` / `ON CONFLICT DO UPDATE` → `INSERT ... ON DUPLICATE
  KEY UPDATE` (with `VALUES(col)` references on MySQL ≤ 8.0.20 –
  works in 5.7 too, the deprecation only matters from 8.0.20 onward and
  the alternative `AS new` syntax breaks 5.7).
* SQLite WAL filesystem fallback (NFS/SMB/FUSE) → not applicable;
  MySQL handles its own durability.

## Multi-tenant kanban

In SQLite each board has its own `kanban.db` file under
`$HERMES_HOME/kanban/<slug>/`. MySQL uses a single database with a
`board_slug VARCHAR(64) NOT NULL DEFAULT 'default'` column on every
table; primary keys and indexes are prefixed with `board_slug`. The
in-place SQL rewrite in `hermes_cli/kanban_db.py` is the follow-up
referenced above.

## Migration from SQLite

The data importer at `scripts/migrate_sqlite_to_mysql.py` (also exposed as
`hermes db import-sqlite`) copies a legacy SQLite store row-by-row into
the configured MySQL backend. It only covers the stores whose code path
is already MySQL-ready — today, `response_store` and `memory_store`. Add
the other two as their full SQL rewrites land.

Semantics:

* **Schema first.** The importer auto-runs the Flyway migrator before
  copying rows; pass `--skip-schema` if you've already applied DDL.
* **`INSERT IGNORE` everywhere.** Re-runs are safe — existing rows are
  not overwritten. To re-seed, truncate the target table first.
* **Backend gate.** Refuses to run unless the active backend is
  `mysql`. No silent fallback.
* **`memory_store` notes.** `content_hash` is recomputed for every
  imported fact (older sqlite rows did not store one). `memory_banks`
  uses `ON DUPLICATE KEY UPDATE` so a re-import refreshes vectors.

Recommended workflow:

```bash
# 1. Provision MySQL schema (idempotent)
hermes db migrate --backend mysql

# 2. Stop any agent processes still writing to SQLite
hermes stop

# 3. Bulk import per store
hermes db import-sqlite --store response_store \
    --src ~/.hermes/response_store.db
hermes db import-sqlite --store memory_store \
    --src ~/.hermes/memory_store.db

# Dry-run first to inspect row counts:
hermes db import-sqlite --store memory_store \
    --src ~/.hermes/memory_store.db --dry-run

# 4. Flip config (env or storage.backend in cli-config.yaml)
export HERMES_DB_BACKEND=mysql

# 5. Smoke-test
hermes status
```

For `state` and `kanban`, keep `HERMES_DB_BACKEND=sqlite` until their
native MySQL paths land — the guard rails will refuse a half-migrated
launch.

## Backups and operational hygiene

* SQLite mode: `hermes backup` / `scripts/backup.py` continues to work —
  file copy + `sqlite3.backup()` for WAL-safe snapshots.
* MySQL mode: lean on the existing MySQL tooling at the host
  (`mysqldump`, replication, snapshots). Hermes Agent ships no MySQL
  backup helper; the database is treated as managed infrastructure.
  The `hermes backup` command prints a notice when it detects the
  MySQL backend so a config-only zip isn't mistaken for a full backup.
* `hermes_cli/profile_distribution.py` is backend-agnostic at the
  filesystem level: the `*.db` files are listed under `USER_OWNED_EXCLUDE`
  so they're never bundled into a distribution — in MySQL mode they
  simply aren't on disk in the first place.

## Troubleshooting

* **`hermes_state.SessionDB: MySQL backend is not yet wired ...`** —
  expected. Drop `storage.backend = mysql` until the state-mysql
  follow-up lands.
* **`hermes_cli.kanban_db: MySQL backend is not yet wired ...`** —
  same story for kanban.
* **`PyMySQL is required for storage.backend=mysql`** — install the
  extra: `pip install 'hermes-agent[mysql]'`.
* **`schema_version checksum mismatch for V<N>__<...>.sql`** — somebody
  edited an applied migration. Either revert or write a new `V<N+1>` and
  let the migrator forward-roll.
