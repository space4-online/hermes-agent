-- Hermes Agent — memory_store (holographic memory) V1 (MySQL)
--
-- Mirrors plugins/memory/holographic/store.py SCHEMA.
-- The HRR vector is stored as LONGBLOB (numpy float32 dump can run
-- into the megabytes for high-dim banks).
-- FTS5 facts_fts is replaced by a FULLTEXT(content, tags) index on
-- ``facts`` itself.

CREATE TABLE IF NOT EXISTS facts (
    fact_id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    content          LONGTEXT NOT NULL,
    content_hash     CHAR(64)  NOT NULL,
    category         VARCHAR(64)  NOT NULL DEFAULT 'general',
    tags             LONGTEXT     NOT NULL DEFAULT (''),
    trust_score      DOUBLE       NOT NULL DEFAULT 0.5,
    retrieval_count  INT          NOT NULL DEFAULT 0,
    helpful_count    INT          NOT NULL DEFAULT 0,
    created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                              ON UPDATE CURRENT_TIMESTAMP,
    hrr_vector       LONGBLOB,
    UNIQUE KEY uq_facts_content_hash (content_hash),
    KEY idx_facts_trust    (trust_score),
    KEY idx_facts_category (category),
    FULLTEXT KEY ft_facts (content, tags) WITH PARSER ngram
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;

-- Note on content uniqueness:
-- SQLite uses ``content TEXT UNIQUE``.  MySQL won't index a LONGTEXT
-- without a prefix length, so we add a ``content_hash`` (sha256 hex)
-- column maintained at the application layer (``MemoryStore.add_fact``
-- already computes a stable hash).  Backwards-compat shim in the
-- holographic adapter populates ``content_hash`` even when the
-- migration path runs against an older app version.

CREATE TABLE IF NOT EXISTS entities (
    entity_id    BIGINT AUTO_INCREMENT PRIMARY KEY,
    name         VARCHAR(255) NOT NULL,
    entity_type  VARCHAR(64)  NOT NULL DEFAULT 'unknown',
    aliases      LONGTEXT     NOT NULL DEFAULT (''),
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_entities_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;

CREATE TABLE IF NOT EXISTS fact_entities (
    fact_id    BIGINT NOT NULL,
    entity_id  BIGINT NOT NULL,
    PRIMARY KEY (fact_id, entity_id),
    KEY idx_fact_entities_entity (entity_id),
    CONSTRAINT fk_fact_entities_fact
        FOREIGN KEY (fact_id) REFERENCES facts(fact_id) ON DELETE CASCADE,
    CONSTRAINT fk_fact_entities_entity
        FOREIGN KEY (entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS memory_banks (
    bank_id     BIGINT AUTO_INCREMENT PRIMARY KEY,
    bank_name   VARCHAR(128) NOT NULL,
    vector      LONGBLOB     NOT NULL,
    dim         INT          NOT NULL,
    fact_count  INT          NOT NULL DEFAULT 0,
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                            ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_memory_banks_name (bank_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;
