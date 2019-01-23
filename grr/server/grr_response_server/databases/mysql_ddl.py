#!/usr/bin/env python
"""A collection of DDL for use by the mysql database implementation."""

from __future__ import absolute_import
from __future__ import division

SCHEMA_SETUP = [
    """
CREATE TABLE IF NOT EXISTS artifacts(
    name_hash BINARY(32) PRIMARY KEY,
    definition MEDIUMBLOB
)""", """
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
    owner_username_hash BINARY(32),
    label VARCHAR(95),
    owner_username VARCHAR(254),
    PRIMARY KEY (client_id, owner_username_hash, label),
    -- TODO: Add FOREIGN KEY when owner does not use `GRR` anymore.
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
)""", """
CREATE INDEX IF NOT EXISTS owner_label_idx
    -- Maximum index length is 767 bytes = 191 UTF-8 characters. Divide evenly.
    ON client_labels(owner_username(95), label)
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
    keyword_hash BINARY(32),
    keyword VARCHAR(255),
    timestamp DATETIME(6),
    PRIMARY KEY (client_id, keyword_hash),
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
)""", """
CREATE TABLE IF NOT EXISTS client_stats(
    client_id BIGINT UNSIGNED,
    payload MEDIUMBLOB,
    timestamp DATETIME(6),
    -- Timestamp is the first part of the primary key, because both
    -- ReadClientStats and DeleteOldClientStats filter by timestamp, but only
    -- ReadClientStats filters by client_id.
    PRIMARY KEY (timestamp, client_id),
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
)""", """
CREATE TABLE IF NOT EXISTS grr_users(
    username_hash BINARY(32) PRIMARY KEY,
    username VARCHAR(254),
    password VARBINARY(255),
    ui_mode INT UNSIGNED,
    canary_mode BOOL,
    user_type INT UNSIGNED
)""", """
CREATE INDEX IF NOT EXISTS username_idx ON grr_users(username(191))
""", """
CREATE TABLE IF NOT EXISTS approval_request(
    username_hash BINARY(32),
    approval_type INT UNSIGNED,
    subject_id VARCHAR(128),
    approval_id BIGINT UNSIGNED,
    timestamp DATETIME(6),
    expiration_time DATETIME(6),
    approval_request MEDIUMBLOB,
    PRIMARY KEY (username_hash, approval_id),
    FOREIGN KEY (username_hash) REFERENCES grr_users (username_hash)
)""", """
CREATE INDEX IF NOT EXISTS by_username_type_subject
ON approval_request(username_hash, approval_type, subject_id)
""", """
CREATE TABLE IF NOT EXISTS approval_grant(
    username_hash BINARY(32),
    approval_id BIGINT UNSIGNED,
    grantor_username_hash BINARY(32),
    timestamp DATETIME(6),
    PRIMARY KEY (username_hash, approval_id, grantor_username_hash, timestamp),
    FOREIGN KEY (username_hash) REFERENCES grr_users (username_hash),
    FOREIGN KEY (grantor_username_hash) REFERENCES grr_users (username_hash)
)""", """
CREATE TABLE IF NOT EXISTS user_notification(
    username_hash BINARY(32),
    timestamp DATETIME(6),
    notification_state INT UNSIGNED,
    notification MEDIUMBLOB,
    PRIMARY KEY (username_hash, timestamp),
    FOREIGN KEY (username_hash) REFERENCES grr_users (username_hash)
)""", """
CREATE TABLE IF NOT EXISTS api_audit_entry(
    username_hash BINARY(32),
    router_method_name VARCHAR(128),
    timestamp DATETIME(6) DEFAULT CURRENT_TIMESTAMP,
    details MEDIUMBLOB,
    PRIMARY KEY (username_hash, timestamp),
    FOREIGN KEY (username_hash) REFERENCES grr_users (username_hash)
)""", """
CREATE INDEX IF NOT EXISTS timestamp_idx
ON api_audit_entry(timestamp)
""", """
CREATE INDEX IF NOT EXISTS router_method_name_idx
ON api_audit_entry(router_method_name)
""", """
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
    current_run_id VARCHAR(128),
    enabled BOOL,
    forced_run_requested BOOL,
    last_run_time DATETIME(6),
    last_run_status INT UNSIGNED,
    state MEDIUMBLOB,
    leased_until DATETIME(6),
    leased_by VARCHAR(128),
    PRIMARY KEY (job_id)
)""", """
CREATE TABLE IF NOT EXISTS cron_job_runs(
    job_id VARCHAR(128),
    run_id VARCHAR(128),
    write_time DATETIME(6),
    run MEDIUMBLOB,
    PRIMARY KEY (job_id, run_id),
    FOREIGN KEY (job_id) REFERENCES cron_jobs (job_id)
)""", """
CREATE TABLE IF NOT EXISTS client_messages(
    client_id BIGINT UNSIGNED,
    message_id BIGINT UNSIGNED,
    timestamp DATETIME(6),
    message MEDIUMBLOB,
    leased_until DATETIME(6),
    leased_by VARCHAR(128),
    leased_count INT DEFAULT 0,
    PRIMARY KEY (client_id, message_id),
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
)""", """
CREATE TABLE IF NOT EXISTS flows(
    client_id BIGINT UNSIGNED,
    flow_id BIGINT UNSIGNED,
    long_flow_id VARCHAR(255),
    parent_flow_id BIGINT UNSIGNED,
    flow BLOB,
    client_crash_info MEDIUMBLOB,
    next_request_to_process INT UNSIGNED,
    pending_termination MEDIUMBLOB,
    processing_deadline DATETIME(6),
    processing_on VARCHAR(128),
    processing_since DATETIME(6),
    timestamp DATETIME(6),
    last_update DATETIME(6),
    PRIMARY KEY (client_id, flow_id),
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
)""", """
CREATE INDEX IF NOT EXISTS timestamp_idx ON flows(timestamp)
""", """
CREATE TABLE IF NOT EXISTS flow_requests(
    client_id BIGINT UNSIGNED,
    flow_id BIGINT UNSIGNED,
    request_id BIGINT UNSIGNED,
    needs_processing BOOL,
    responses_expected BIGINT UNSIGNED,
    request MEDIUMBLOB,
    timestamp DATETIME(6),
    PRIMARY KEY (client_id, flow_id, request_id),
    FOREIGN KEY (client_id, flow_id) REFERENCES flows(client_id, flow_id)
)""", """
CREATE TABLE IF NOT EXISTS flow_responses(
    client_id BIGINT UNSIGNED,
    flow_id BIGINT UNSIGNED,
    request_id BIGINT UNSIGNED,
    response_id BIGINT UNSIGNED,
    response MEDIUMBLOB,
    status MEDIUMBLOB,
    iterator MEDIUMBLOB,
    timestamp DATETIME(6),
    PRIMARY KEY (client_id, flow_id, request_id, response_id),
    FOREIGN KEY (client_id, flow_id, request_id)
    REFERENCES flow_requests(client_id, flow_id, request_id)
)""", """
CREATE TABLE IF NOT EXISTS flow_processing_requests(
    client_id BIGINT UNSIGNED,
    flow_id BIGINT UNSIGNED,
    timestamp DATETIME(6),
    request MEDIUMBLOB,
    delivery_time DATETIME(6),
    leased_until DATETIME(6),
    leased_by VARCHAR(128),
    PRIMARY KEY (client_id, flow_id, timestamp),
    FOREIGN KEY (client_id, flow_id) REFERENCES flows(client_id, flow_id)
)"""
]
