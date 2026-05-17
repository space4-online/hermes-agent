-- Hermes Agent — state store V1 (initial schema for MySQL)
--
-- Mirrors the live SQLite schema in ``hermes_state.SCHEMA_SQL`` /
-- ``FTS_SQL`` / ``FTS_TRIGRAM_SQL`` after applying every numbered
-- column-add migration (current ``hermes_state.SCHEMA_VERSION = 11``).
--
-- Differences vs SQLite:
--   * Auto-increment PK uses ``BIGINT AUTO_INCREMENT PRIMARY KEY``.
--   * Floating-point uses ``DOUBLE``.
--   * Long TEXT columns map to ``LONGTEXT`` (no length budget on the
--     row).
--   * FTS5 virtual tables and their triggers are replaced by an
--     in-place ``FULLTEXT`` index on ``messages.content`` with the
--     ``ngram`` parser (CJK-friendly).  The redundant ``messages_fts``
--     and ``messages_fts_trigram`` SQLite tables are *not* recreated;
--     ``hermes_db.dialect.fts_match`` builds backend-specific WHERE
--     fragments so call sites need no branching.
--   * Foreign keys keep ``REFERENCES sessions(id)`` semantics; we use
--     ``ON DELETE`` action policies that match the SQLite triggers
--     written elsewhere in the codebase.
--
-- ``schema_version`` is provisioned by the Flyway-style runner
-- (``hermes_db.migrate``) — do *not* recreate it here.

CREATE TABLE IF NOT EXISTS sessions (
    id                  VARCHAR(64)  NOT NULL,
    source              VARCHAR(32)  NOT NULL,
    user_id             VARCHAR(128),
    model               VARCHAR(128),
    model_config        LONGTEXT,
    system_prompt       LONGTEXT,
    parent_session_id   VARCHAR(64),
    started_at          DOUBLE       NOT NULL,
    ended_at            DOUBLE,
    end_reason          VARCHAR(64),
    message_count       INT          NOT NULL DEFAULT 0,
    tool_call_count     INT          NOT NULL DEFAULT 0,
    input_tokens        BIGINT       NOT NULL DEFAULT 0,
    output_tokens       BIGINT       NOT NULL DEFAULT 0,
    cache_read_tokens   BIGINT       NOT NULL DEFAULT 0,
    cache_write_tokens  BIGINT       NOT NULL DEFAULT 0,
    reasoning_tokens    BIGINT       NOT NULL DEFAULT 0,
    billing_provider    VARCHAR(64),
    billing_base_url    VARCHAR(255),
    billing_mode        VARCHAR(32),
    estimated_cost_usd  DOUBLE,
    actual_cost_usd     DOUBLE,
    cost_status         VARCHAR(32),
    cost_source         VARCHAR(32),
    pricing_version     VARCHAR(32),
    title               VARCHAR(512),
    api_call_count      INT          NOT NULL DEFAULT 0,
    handoff_state       VARCHAR(32),
    handoff_platform    VARCHAR(64),
    handoff_error       LONGTEXT,
    PRIMARY KEY (id),
    KEY idx_sessions_source  (source),
    KEY idx_sessions_parent  (parent_session_id),
    KEY idx_sessions_started (started_at),
    CONSTRAINT fk_sessions_parent
        FOREIGN KEY (parent_session_id) REFERENCES sessions(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;

CREATE TABLE IF NOT EXISTS messages (
    id                       BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id               VARCHAR(64)  NOT NULL,
    role                     VARCHAR(32)  NOT NULL,
    content                  LONGTEXT,
    tool_call_id             VARCHAR(128),
    tool_calls               LONGTEXT,
    tool_name                VARCHAR(128),
    timestamp                DOUBLE       NOT NULL,
    token_count              INT,
    finish_reason            VARCHAR(64),
    reasoning                LONGTEXT,
    reasoning_content        LONGTEXT,
    reasoning_details        LONGTEXT,
    codex_reasoning_items    LONGTEXT,
    codex_message_items      LONGTEXT,
    KEY idx_messages_session (session_id, timestamp),
    FULLTEXT KEY ft_messages_content (content) WITH PARSER ngram,
    CONSTRAINT fk_messages_session
        FOREIGN KEY (session_id) REFERENCES sessions(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;

CREATE TABLE IF NOT EXISTS state_meta (
    `key`   VARCHAR(128) NOT NULL,
    value   LONGTEXT,
    PRIMARY KEY (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Telegram DM topic-mode tables — opt-in feature, but creating them
-- up-front avoids first-use latency on the gateway hot path.
CREATE TABLE IF NOT EXISTS telegram_dm_topic_mode (
    chat_id     VARCHAR(64) NOT NULL,
    user_id     VARCHAR(64) NOT NULL,
    enabled     TINYINT(1)  NOT NULL DEFAULT 1,
    enabled_at  DOUBLE      NOT NULL,
    PRIMARY KEY (chat_id, user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS telegram_dm_topic_bindings (
    chat_id      VARCHAR(64)  NOT NULL,
    thread_id    VARCHAR(64)  NOT NULL,
    session_id   VARCHAR(64)  NOT NULL,
    bound_at     DOUBLE       NOT NULL,
    PRIMARY KEY (chat_id, thread_id),
    KEY idx_tg_bindings_session (session_id),
    CONSTRAINT fk_tg_bindings_session
        FOREIGN KEY (session_id) REFERENCES sessions(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
