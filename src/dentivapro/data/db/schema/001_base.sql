-- Dentiva Pro schema migration 001 — foundation
--
-- This migration creates the tables the application needs to start, to record its own metadata and
-- to store business settings. Domain tables (patients, clinical, billing, inventory, security and
-- the audit trail) are added by later migrations so that every step is small, reviewable and safe to
-- apply to an existing clinic database.

CREATE TABLE app_meta (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE settings (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    updated_by INTEGER
);

CREATE TABLE sequence (
    name       TEXT PRIMARY KEY,
    prefix     TEXT NOT NULL DEFAULT '',
    padding    INTEGER NOT NULL DEFAULT 5 CHECK (padding BETWEEN 1 AND 12),
    next_value INTEGER NOT NULL DEFAULT 1 CHECK (next_value >= 1)
);

CREATE TABLE machine_registry (
    installation_id TEXT PRIMARY KEY,
    first_seen_at   TEXT NOT NULL,
    last_seen_at    TEXT NOT NULL,
    app_version     TEXT NOT NULL,
    machine_label   TEXT NOT NULL
);

CREATE TABLE schema_history (
    version    INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    applied_at TEXT NOT NULL,
    app_version TEXT NOT NULL,
    duration_ms INTEGER NOT NULL
);

CREATE INDEX ix_settings_updated_at ON settings (updated_at);
