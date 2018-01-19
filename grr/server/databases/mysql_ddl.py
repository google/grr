#!/usr/bin/env python
"""A collection of DDL for use by the mysql database implementation."""

SCHEMA_SETUP = [
    """
CREATE TABLE IF NOT EXISTS clients(
    client_id BIGINT UNSIGNED PRIMARY KEY,
    last_timestamp BIGINT,
    fleetspeak_enabled BOOL NOT NULL,
    certificate BLOB
)""",
    """
CREATE TABLE IF NOT EXISTS client_labels(
    client_id BIGINT UNSIGNED,
    owner VARCHAR(64),
    label VARCHAR(64),
    PRIMARY KEY (client_id, owner, label),
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
)""",
]
