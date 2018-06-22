#!/usr/bin/env python
"""A collection of DDL for use by the mysql database implementation."""

SCHEMA_SETUP = [
    """
CREATE TABLE IF NOT EXISTS clients(
    client_id BIGINT UNSIGNED PRIMARY KEY,
    last_client_timestamp DATETIME(6),
    last_startup_timestamp DATETIME(6),
    last_crash_timestamp DATETIME(6),
    fleetspeak_enabled BOOL,
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
    label VARCHAR(64) CHARACTER SET utf8,
    PRIMARY KEY (client_id, owner, label),
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
)""", """
CREATE INDEX IF NOT EXISTS owner_label_idx ON client_labels(owner, label)
""", """
CREATE TABLE IF NOT EXISTS client_snapshot_history(
    client_id BIGINT UNSIGNED,
    timestamp DATETIME(6),
    client_snapshot MEDIUMBLOB,
    PRIMARY KEY (client_id, timestamp),
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
)""", """
CREATE TABLE IF NOT EXISTS client_startup_history(
    client_id BIGINT UNSIGNED,
    timestamp DATETIME(6),
    startup_info MEDIUMBLOB,
    PRIMARY KEY (client_id, timestamp),
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
)""", """
CREATE TABLE IF NOT EXISTS client_crash_history(
    client_id BIGINT UNSIGNED,
    timestamp DATETIME(6),
    crash_info MEDIUMBLOB,
    PRIMARY KEY (client_id, timestamp),
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
)""", """
CREATE TABLE IF NOT EXISTS client_keywords(
    client_id BIGINT UNSIGNED,
    keyword VARCHAR(255) CHARACTER SET utf8,
    timestamp DATETIME(6),
    PRIMARY KEY (client_id, keyword),
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
)""", """
CREATE INDEX IF NOT EXISTS keyword_client_idx ON client_keywords(keyword(64))
""", """
CREATE TABLE IF NOT EXISTS grr_users(
    username VARCHAR(128) PRIMARY KEY,
    password VARBINARY(255),
    ui_mode INT UNSIGNED,
    canary_mode BOOL,
    user_type INT UNSIGNED
)""", """
CREATE TABLE IF NOT EXISTS approval_request(
    username VARCHAR(128),
    approval_type INT UNSIGNED,
    subject_id VARCHAR(128),
    approval_id BIGINT UNSIGNED,
    timestamp DATETIME(6),
    expiration_time DATETIME(6),
    approval_request MEDIUMBLOB,
    PRIMARY KEY (username, approval_id),
    FOREIGN KEY (username) REFERENCES grr_users (username)
)""", """
CREATE INDEX IF NOT EXISTS by_username_type_subject
ON approval_request(username, approval_type, subject_id)
""", """
CREATE TABLE IF NOT EXISTS approval_grant(
    username VARCHAR(128),
    approval_id BIGINT UNSIGNED,
    grantor_username VARCHAR(128),
    timestamp DATETIME(6),
    PRIMARY KEY (username, approval_id, grantor_username, timestamp),
    FOREIGN KEY (username) REFERENCES grr_users (username)
)""", """
CREATE TABLE IF NOT EXISTS user_notification(
    username VARCHAR(128),
    timestamp DATETIME(6),
    notification_state INT UNSIGNED,
    notification MEDIUMBLOB,
    PRIMARY KEY (username, timestamp),
    FOREIGN KEY (username) REFERENCES grr_users (username)
)""", """
CREATE TABLE IF NOT EXISTS audit_event(
    username VARCHAR(128),
    urn VARCHAR(128),
    client_id BIGINT UNSIGNED,
    timestamp DATETIME(6),
    details MEDIUMBLOB
)""", """
CREATE TABLE IF NOT EXISTS message_handler_requests(
    handlername VARCHAR(128),
    timestamp DATETIME(6),
    request_id INT UNSIGNED,
    request MEDIUMBLOB,
    leased_until DATETIME(6),
    leased_by VARCHAR(128),
    PRIMARY KEY (handlername, request_id)
)""", """
CREATE TABLE IF NOT EXISTS foreman_rules(
    hunt_id VARCHAR(128),
    expiration_time DATETIME(6),
    rule MEDIUMBLOB,
    PRIMARY KEY (hunt_id)
)""", """
CREATE TABLE IF NOT EXISTS cron_jobs(
    job_id VARCHAR(128),
    job MEDIUMBLOB,
    create_time DATETIME(6),
    current_run_id INT UNSIGNED,
    disabled BOOL,
    last_run_time DATETIME(6),
    last_run_status INT UNSIGNED,
    state MEDIUMBLOB,
    leased_until DATETIME(6),
    leased_by VARCHAR(128),
    PRIMARY KEY (job_id)
)"""
]
