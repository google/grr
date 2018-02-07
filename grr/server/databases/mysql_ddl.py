#!/usr/bin/env python
"""A collection of DDL for use by the mysql database implementation."""

SCHEMA_SETUP = [
    """
CREATE TABLE IF NOT EXISTS clients(
    client_id BIGINT UNSIGNED PRIMARY KEY,
    last_timestamp DATETIME(6),
    fleetspeak_enabled BOOL NOT NULL,
    certificate BLOB,
    last_ping DATETIME(6),
    last_clock DATETIME(6),
    last_ip VARCHAR(64),
    last_foreman DATETIME(6),
    first_seen DATETIME(6)
)""", """
CREATE TABLE IF NOT EXISTS client_labels(
    client_id BIGINT UNSIGNED,
    owner VARCHAR(64),
    label VARCHAR(64),
    PRIMARY KEY (client_id, owner, label),
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
)""", """
CREATE TABLE IF NOT EXISTS client_history(
    client_id BIGINT UNSIGNED,
    timestamp DATETIME,
    client_snapshot MEDIUMBLOB,
    PRIMARY KEY (client_id, timestamp),
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
)""", """
CREATE TABLE IF NOT EXISTS client_keywords(
    client_id BIGINT UNSIGNED,
    keyword VARCHAR(255),
    timestamp DATETIME,
    PRIMARY KEY (client_id, keyword),
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
)""", """
CREATE INDEX IF NOT EXISTS keyword_client_idx ON client_keywords(keyword(64))
""", """
CREATE TABLE IF NOT EXISTS grr_users(
    username VARCHAR(128) PRIMARY KEY,
    password VARBINARY(255),
    ui_mode BIGINT UNSIGNED,
    canary_mode BOOL
)"""
]
