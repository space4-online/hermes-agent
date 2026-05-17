-- Hermes Agent — response_store V1 (MySQL)
--
-- Mirrors gateway/platforms/api_server.py ResponseStore tables.
-- This store is a small KV cache (the OpenAI ``previous_response_id``
-- chain) so we keep it deliberately tiny.

CREATE TABLE IF NOT EXISTS responses (
    response_id   VARCHAR(128) NOT NULL,
    data          LONGTEXT     NOT NULL,
    accessed_at   DOUBLE       NOT NULL,
    PRIMARY KEY (response_id),
    KEY idx_responses_accessed (accessed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;

CREATE TABLE IF NOT EXISTS conversations (
    name         VARCHAR(255) NOT NULL,
    response_id  VARCHAR(128) NOT NULL,
    PRIMARY KEY (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
