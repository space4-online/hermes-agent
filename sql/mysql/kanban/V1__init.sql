-- Hermes Agent — kanban store V1 (initial schema for MySQL)
--
-- Mirrors the SQLite schema in ``hermes_cli.kanban_db.SCHEMA_SQL``.
-- The kanban DB never used FTS, so this file is straight DDL.
--
-- Multi-tenancy note (MySQL only):
--   In the SQLite world each Kanban *board* lives in its own
--   ``kanban.db`` file (``$HERMES_HOME/kanban/boards/<slug>/kanban.db``).
--   Migrating that to a single MySQL service would require N database
--   handles, which is needlessly fragile.  Instead, every table here
--   carries an additional ``board_slug VARCHAR(64) NOT NULL`` column
--   (default ``'default'`` matching the back-compat board) that the
--   application layer transparently injects on every read/write so
--   one MySQL schema can host all boards.  Cross-board queries (e.g.
--   the gateway's notifier daemon) become trivial.
--   Indexes are extended with ``board_slug`` as a leading column to
--   keep B-tree locality per board.

CREATE TABLE IF NOT EXISTS tasks (
    board_slug            VARCHAR(64)  NOT NULL DEFAULT 'default',
    id                    VARCHAR(64)  NOT NULL,
    title                 VARCHAR(512) NOT NULL,
    body                  LONGTEXT,
    assignee              VARCHAR(128),
    status                VARCHAR(32)  NOT NULL,
    priority              INT          NOT NULL DEFAULT 0,
    created_by            VARCHAR(128),
    created_at            BIGINT       NOT NULL,
    started_at            BIGINT,
    completed_at          BIGINT,
    workspace_kind        VARCHAR(32)  NOT NULL DEFAULT 'scratch',
    workspace_path        VARCHAR(512),
    claim_lock            VARCHAR(128),
    claim_expires         BIGINT,
    tenant                VARCHAR(64),
    result                LONGTEXT,
    idempotency_key       VARCHAR(128),
    consecutive_failures  INT          NOT NULL DEFAULT 0,
    worker_pid            INT,
    last_failure_error    LONGTEXT,
    max_runtime_seconds   INT,
    last_heartbeat_at     BIGINT,
    current_run_id        BIGINT,
    workflow_template_id  VARCHAR(64),
    current_step_key      VARCHAR(128),
    skills                LONGTEXT,
    max_retries           INT,
    PRIMARY KEY (board_slug, id),
    KEY idx_tasks_assignee_status (board_slug, assignee, status),
    KEY idx_tasks_status          (board_slug, status),
    KEY idx_tasks_tenant          (board_slug, tenant),
    KEY idx_tasks_idempotency     (board_slug, idempotency_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;

CREATE TABLE IF NOT EXISTS task_links (
    board_slug VARCHAR(64) NOT NULL DEFAULT 'default',
    parent_id  VARCHAR(64) NOT NULL,
    child_id   VARCHAR(64) NOT NULL,
    PRIMARY KEY (board_slug, parent_id, child_id),
    KEY idx_links_child  (board_slug, child_id),
    KEY idx_links_parent (board_slug, parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS task_comments (
    id         BIGINT AUTO_INCREMENT PRIMARY KEY,
    board_slug VARCHAR(64) NOT NULL DEFAULT 'default',
    task_id    VARCHAR(64) NOT NULL,
    author     VARCHAR(128) NOT NULL,
    body       LONGTEXT NOT NULL,
    created_at BIGINT NOT NULL,
    KEY idx_comments_task (board_slug, task_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;

CREATE TABLE IF NOT EXISTS task_events (
    id         BIGINT AUTO_INCREMENT PRIMARY KEY,
    board_slug VARCHAR(64) NOT NULL DEFAULT 'default',
    task_id    VARCHAR(64) NOT NULL,
    run_id     BIGINT,
    kind       VARCHAR(64) NOT NULL,
    payload    LONGTEXT,
    created_at BIGINT NOT NULL,
    KEY idx_events_task (board_slug, task_id, created_at),
    KEY idx_events_run  (board_slug, run_id, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;

CREATE TABLE IF NOT EXISTS task_runs (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    board_slug          VARCHAR(64) NOT NULL DEFAULT 'default',
    task_id             VARCHAR(64) NOT NULL,
    profile             VARCHAR(128),
    step_key            VARCHAR(128),
    status              VARCHAR(32) NOT NULL,
    claim_lock          VARCHAR(128),
    claim_expires       BIGINT,
    worker_pid          INT,
    max_runtime_seconds INT,
    last_heartbeat_at   BIGINT,
    started_at          BIGINT      NOT NULL,
    ended_at            BIGINT,
    outcome             VARCHAR(32),
    summary             LONGTEXT,
    metadata            LONGTEXT,
    error               LONGTEXT,
    KEY idx_runs_task   (board_slug, task_id, started_at),
    KEY idx_runs_status (board_slug, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;

CREATE TABLE IF NOT EXISTS kanban_notify_subs (
    board_slug       VARCHAR(64)  NOT NULL DEFAULT 'default',
    task_id          VARCHAR(64)  NOT NULL,
    platform         VARCHAR(64)  NOT NULL,
    chat_id          VARCHAR(64)  NOT NULL,
    thread_id        VARCHAR(64)  NOT NULL DEFAULT '',
    user_id          VARCHAR(64),
    notifier_profile VARCHAR(128),
    created_at       BIGINT       NOT NULL,
    last_event_id    BIGINT       NOT NULL DEFAULT 0,
    PRIMARY KEY (board_slug, task_id, platform, chat_id, thread_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
