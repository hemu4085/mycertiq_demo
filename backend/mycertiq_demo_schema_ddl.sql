
-- MyCertiQ Demo - Full Relational Schema (40 tables)
-- File: mycertiq_demo_schema_ddl.sql
-- Postgres + pgvector

BEGIN;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- =========================================
-- 1. System & Lookup Tables
-- =========================================

CREATE TABLE country_lookup (
    country_code      varchar(2) PRIMARY KEY,
    country_name      varchar(100) NOT NULL
);

CREATE TABLE state_lookup (
    state_code        varchar(3) PRIMARY KEY,
    state_name        varchar(100) NOT NULL,
    country_code      varchar(2) NOT NULL REFERENCES country_lookup(country_code)
);

CREATE TABLE user_account (
    id                bigserial PRIMARY KEY,
    email             varchar(255) UNIQUE NOT NULL,
    password_hash     varchar(255) NOT NULL,
    role              varchar(50) NOT NULL, -- admin, physician, staff, partner
    is_active         boolean NOT NULL DEFAULT true,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE api_key (
    id                bigserial PRIMARY KEY,
    user_account_id   bigint NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
    api_key_hash      varchar(255) NOT NULL UNIQUE,
    label             varchar(100),
    is_active         boolean NOT NULL DEFAULT true,
    created_at        timestamptz NOT NULL DEFAULT now(),
    last_used_at      timestamptz
);

CREATE TABLE file_store (
    id                bigserial PRIMARY KEY,
    storage_path      text NOT NULL,
    mime_type         varchar(255),
    original_filename varchar(255),
    file_size_bytes   bigint,
    uploaded_at       timestamptz NOT NULL DEFAULT now(),
    uploaded_by_id    bigint REFERENCES user_account(id)
);

CREATE TABLE audit_log (
    id                bigserial PRIMARY KEY,
    user_account_id   bigint REFERENCES user_account(id),
    action            varchar(255) NOT NULL,
    metadata          jsonb,
    created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE task_queue (
    id                bigserial PRIMARY KEY,
    task_type         varchar(100) NOT NULL,
    payload           jsonb NOT NULL,
    status            varchar(50) NOT NULL DEFAULT 'pending', -- pending, running, done, failed
    created_at        timestamptz NOT NULL DEFAULT now(),
    started_at        timestamptz,
    completed_at      timestamptz,
    error_message     text
);

-- =========================================
-- 2. Core Physician Domain
-- =========================================

CREATE TABLE specialty (
    id                bigserial PRIMARY KEY,
    code              varchar(50) UNIQUE NOT NULL,
    name              varchar(255) NOT NULL,
    board_name        varchar(255),
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE physician (
    id                bigserial PRIMARY KEY,
    user_account_id   bigint REFERENCES user_account(id),
    npi               varchar(20),
    first_name        varchar(100) NOT NULL,
    last_name         varchar(100) NOT NULL,
    email             varchar(255),
    primary_specialty_id bigint REFERENCES specialty(id),
    status            varchar(50) NOT NULL DEFAULT 'active',
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE physician_specialty (
    id                bigserial PRIMARY KEY,
    physician_id      bigint NOT NULL REFERENCES physician(id) ON DELETE CASCADE,
    specialty_id      bigint NOT NULL REFERENCES specialty(id),
    is_primary        boolean NOT NULL DEFAULT false,
    created_at        timestamptz NOT NULL DEFAULT now(),
    UNIQUE (physician_id, specialty_id)
);

CREATE TABLE physician_license (
    id                bigserial PRIMARY KEY,
    physician_id      bigint NOT NULL REFERENCES physician(id) ON DELETE CASCADE,
    license_number    varchar(100) NOT NULL,
    state_code        varchar(3) REFERENCES state_lookup(state_code),
    board_name        varchar(255),
    issue_date        date,
    expiry_date       date,
    status            varchar(50) NOT NULL DEFAULT 'active'
);

-- =========================================
-- 3. Requirements System
-- =========================================

CREATE TABLE requirement_master (
    id                bigserial PRIMARY KEY,
    code              varchar(100) UNIQUE NOT NULL,
    name              varchar(255) NOT NULL,
    authority_type    varchar(50) NOT NULL, -- state, board, hospital, federal
    description       text,
    total_credits_required numeric(6,2),
    min_live_credits  numeric(6,2),
    min_specialty_credits numeric(6,2),
    is_active         boolean NOT NULL DEFAULT true,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE requirement_cycle_template (
    id                bigserial PRIMARY KEY,
    requirement_id    bigint NOT NULL REFERENCES requirement_master(id) ON DELETE CASCADE,
    duration_months   integer NOT NULL,
    rolling           boolean NOT NULL DEFAULT false,
    default_start_anchor date,
    created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE requirement_topic_map (
    id                bigserial PRIMARY KEY,
    requirement_id    bigint NOT NULL REFERENCES requirement_master(id) ON DELETE CASCADE,
    cme_topic_id      bigint NOT NULL,
    min_credits       numeric(6,2),
    created_at        timestamptz NOT NULL DEFAULT now()
    -- FK to cme_topic added after cme_topic definition
);

CREATE TABLE requirement_override (
    id                bigserial PRIMARY KEY,
    requirement_id    bigint NOT NULL REFERENCES requirement_master(id) ON DELETE CASCADE,
    physician_id      bigint NOT NULL REFERENCES physician(id) ON DELETE CASCADE,
    override_reason   text,
    override_total_credits numeric(6,2),
    effective_from    date,
    effective_to      date,
    created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE requirement_provider_map (
    id                bigserial PRIMARY KEY,
    requirement_id    bigint NOT NULL REFERENCES requirement_master(id) ON DELETE CASCADE,
    cme_provider_id   bigint NOT NULL,
    created_at        timestamptz NOT NULL DEFAULT now()
    -- FK to cme_provider added after cme_provider definition
);

CREATE TABLE requirement_state_map (
    id                bigserial PRIMARY KEY,
    requirement_id    bigint NOT NULL REFERENCES requirement_master(id) ON DELETE CASCADE,
    state_code        varchar(3) NOT NULL REFERENCES state_lookup(state_code),
    created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE requirement_specialty_map (
    id                bigserial PRIMARY KEY,
    requirement_id    bigint NOT NULL REFERENCES requirement_master(id) ON DELETE CASCADE,
    specialty_id      bigint NOT NULL REFERENCES specialty(id),
    created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE requirement_document (
    id                bigserial PRIMARY KEY,
    requirement_id    bigint NOT NULL REFERENCES requirement_master(id) ON DELETE CASCADE,
    doc_type          varchar(50) NOT NULL, -- statute, FAQ, PDF, policy
    url               text,
    file_store_id     bigint REFERENCES file_store(id),
    created_at        timestamptz NOT NULL DEFAULT now()
);

-- =========================================
-- 4. CME Metadata Knowledge Graph
-- =========================================

CREATE TABLE cme_topic (
    id                bigserial PRIMARY KEY,
    code              varchar(100) UNIQUE NOT NULL,
    name              varchar(255) NOT NULL,
    parent_id         bigint REFERENCES cme_topic(id),
    depth             integer,
    created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE cme_format (
    id                bigserial PRIMARY KEY,
    code              varchar(50) UNIQUE NOT NULL, -- ONLINE, LIVE, HYBRID
    name              varchar(255) NOT NULL,
    description       text
);

CREATE TABLE cme_provider (
    id                bigserial PRIMARY KEY,
    name              varchar(255) NOT NULL,
    website           text,
    accme_id          varchar(100),
    contact_email     varchar(255),
    phone             varchar(50),
    created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE cme_location (
    id                bigserial PRIMARY KEY,
    venue_name        varchar(255),
    city              varchar(100),
    state_code        varchar(3) REFERENCES state_lookup(state_code),
    country_code      varchar(2) REFERENCES country_lookup(country_code),
    timezone          varchar(100)
);

CREATE TABLE cme_event (
    id                bigserial PRIMARY KEY,
    external_id       varchar(255),
    title             varchar(500) NOT NULL,
    description       text,
    format_id         bigint REFERENCES cme_format(id),
    credit_type       varchar(255),
    max_credits       numeric(6,2),
    url               text,
    location_id       bigint REFERENCES cme_location(id),
    is_active         boolean NOT NULL DEFAULT true,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE cme_event_topic_map (
    id                bigserial PRIMARY KEY,
    cme_event_id      bigint NOT NULL REFERENCES cme_event(id) ON DELETE CASCADE,
    cme_topic_id      bigint NOT NULL REFERENCES cme_topic(id),
    credit_weight     numeric(6,2),
    created_at        timestamptz NOT NULL DEFAULT now(),
    UNIQUE (cme_event_id, cme_topic_id)
);

CREATE TABLE cme_event_provider_map (
    id                bigserial PRIMARY KEY,
    cme_event_id      bigint NOT NULL REFERENCES cme_event(id) ON DELETE CASCADE,
    cme_provider_id   bigint NOT NULL REFERENCES cme_provider(id),
    is_primary        boolean NOT NULL DEFAULT false,
    created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE cme_pricing (
    id                bigserial PRIMARY KEY,
    cme_event_id      bigint NOT NULL REFERENCES cme_event(id) ON DELETE CASCADE,
    audience_type     varchar(100), -- physician, resident, nurse
    price_amount      numeric(10,2),
    currency          varchar(10),
    refund_policy     text,
    created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE cme_schedule (
    id                bigserial PRIMARY KEY,
    cme_event_id      bigint NOT NULL REFERENCES cme_event(id) ON DELETE CASCADE,
    start_datetime    timestamptz NOT NULL,
    end_datetime      timestamptz NOT NULL,
    timezone          varchar(100),
    is_recurring      boolean NOT NULL DEFAULT false,
    created_at        timestamptz NOT NULL DEFAULT now()
);

-- Add FKs that reference CME tables from requirement_* now
ALTER TABLE requirement_topic_map
    ADD CONSTRAINT fk_req_topic_cme_topic
        FOREIGN KEY (cme_topic_id) REFERENCES cme_topic(id);

ALTER TABLE requirement_provider_map
    ADD CONSTRAINT fk_req_provider_cme_provider
        FOREIGN KEY (cme_provider_id) REFERENCES cme_provider(id);

-- =========================================
-- 5. Physician Requirements Tracking
-- =========================================

CREATE TABLE physician_requirement_cycle (
    id                bigserial PRIMARY KEY,
    physician_id      bigint NOT NULL REFERENCES physician(id) ON DELETE CASCADE,
    requirement_id    bigint NOT NULL REFERENCES requirement_master(id) ON DELETE CASCADE,
    start_date        date NOT NULL,
    end_date          date NOT NULL,
    status            varchar(50) NOT NULL DEFAULT 'in_progress', -- in_progress, complete, expired
    created_at        timestamptz NOT NULL DEFAULT now(),
    UNIQUE (physician_id, requirement_id, start_date, end_date)
);

CREATE TABLE physician_requirement_status (
    id                bigserial PRIMARY KEY,
    physician_requirement_cycle_id bigint NOT NULL REFERENCES physician_requirement_cycle(id) ON DELETE CASCADE,
    requirement_id    bigint NOT NULL REFERENCES requirement_master(id),
    required_credits  numeric(6,2),
    completed_credits numeric(6,2) DEFAULT 0,
    remaining_credits numeric(6,2),
    status            varchar(50) NOT NULL DEFAULT 'in_progress', -- in_progress, satisfied, at_risk
    created_at        timestamptz NOT NULL DEFAULT now()
);

-- =========================================
-- 6. CME × Physician Activity
-- =========================================

CREATE TABLE physician_cme_event (
    id                bigserial PRIMARY KEY,
    physician_id      bigint NOT NULL REFERENCES physician(id) ON DELETE CASCADE,
    cme_event_id      bigint NOT NULL REFERENCES cme_event(id) ON DELETE CASCADE,
    registered_at     timestamptz NOT NULL DEFAULT now(),
    registration_status varchar(50) NOT NULL DEFAULT 'registered', -- registered, cancelled, waitlist
    UNIQUE (physician_id, cme_event_id)
);

CREATE TABLE physician_completed_cme (
    id                bigserial PRIMARY KEY,
    physician_id      bigint NOT NULL REFERENCES physician(id) ON DELETE CASCADE,
    cme_event_id      bigint NOT NULL REFERENCES cme_event(id),
    credits_earned    numeric(6,2) NOT NULL,
    completion_date   date NOT NULL,
    certificate_url   text,
    file_store_id     bigint REFERENCES file_store(id),
    created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE physician_saved_cme (
    id                bigserial PRIMARY KEY,
    physician_id      bigint NOT NULL REFERENCES physician(id) ON DELETE CASCADE,
    cme_event_id      bigint NOT NULL REFERENCES cme_event(id) ON DELETE CASCADE,
    saved_at          timestamptz NOT NULL DEFAULT now(),
    priority_tag      varchar(50), -- now, later, wishlist
    UNIQUE (physician_id, cme_event_id)
);

CREATE TABLE physician_gap_snapshot (
    id                bigserial PRIMARY KEY,
    physician_id      bigint NOT NULL REFERENCES physician(id) ON DELETE CASCADE,
    requirement_id    bigint NOT NULL REFERENCES requirement_master(id) ON DELETE CASCADE,
    snapshot_at       timestamptz NOT NULL DEFAULT now(),
    required_credits  numeric(6,2),
    completed_credits numeric(6,2),
    remaining_credits numeric(6,2),
    gap_status        varchar(50) NOT NULL, -- safe, at_risk, non_compliant
    recommended_cme_ids jsonb,
    created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE physician_preference (
    id                bigserial PRIMARY KEY,
    physician_id      bigint NOT NULL UNIQUE REFERENCES physician(id) ON DELETE CASCADE,
    travel_pref       varchar(50), -- local, regional, international
    modality_pref     varchar(50), -- online, live, hybrid
    date_window_pref  varchar(100), -- weekends, weekdays, evenings
    family_constraints text,
    specialty_focus   jsonb,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE physician_requirement_allocation (
    id                bigserial PRIMARY KEY,
    physician_requirement_status_id bigint NOT NULL REFERENCES physician_requirement_status(id) ON DELETE CASCADE,
    completed_cme_id  bigint NOT NULL REFERENCES physician_completed_cme(id) ON DELETE CASCADE,
    allocated_credits numeric(6,2) NOT NULL,
    created_at        timestamptz NOT NULL DEFAULT now()
);

-- =========================================
-- 7. LLM / RAG Layer
-- =========================================

CREATE TABLE semantic_document (
    id                bigserial PRIMARY KEY,
    doc_type          varchar(50) NOT NULL, -- FAQ, policy, PDF, notes
    title             varchar(500) NOT NULL,
    source_url        text,
    file_store_id     bigint REFERENCES file_store(id),
    ingested_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE knowledge_chunk (
    id                bigserial PRIMARY KEY,
    source_type       varchar(50) NOT NULL, -- cme_event, requirement, doc
    source_id         bigint,
    section           varchar(255),
    raw_text          text NOT NULL,
    semantic_document_id bigint REFERENCES semantic_document(id),
    created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE embedding_store (
    id                bigserial PRIMARY KEY,
    knowledge_chunk_id bigint NOT NULL REFERENCES knowledge_chunk(id) ON DELETE CASCADE,
    source_type       varchar(50) NOT NULL,
    source_id         bigint,
    chunk_id          varchar(100),
    chunk_text        text NOT NULL,
    embedding         vector(1536) NOT NULL,
    embedding_model   varchar(100) NOT NULL,
    created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE rag_query_log (
    id                bigserial PRIMARY KEY,
    user_account_id   bigint REFERENCES user_account(id),
    physician_id      bigint REFERENCES physician(id),
    question          text NOT NULL,
    answer_summary    text,
    retrieved_chunk_ids jsonb,
    created_at        timestamptz NOT NULL DEFAULT now()
);

-- =========================================
-- Indexes
-- =========================================

CREATE INDEX idx_physician_license_physician_id
    ON physician_license(physician_id);

CREATE INDEX idx_cme_event_active
    ON cme_event(is_active);

CREATE INDEX idx_cme_schedule_event
    ON cme_schedule(cme_event_id, start_datetime);

CREATE INDEX idx_physician_completed_cme_physician
    ON physician_completed_cme(physician_id, completion_date);

CREATE INDEX idx_embedding_store_vector
    ON embedding_store
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX idx_embedding_store_source
    ON embedding_store(source_type, source_id);

COMMIT;
