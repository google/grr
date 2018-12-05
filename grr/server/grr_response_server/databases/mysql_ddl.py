#!/usr/bin/env python
"""A collection of DDL for use by the mysql database implementation."""

from __future__ import absolute_import
from __future__ import division

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
CREATE TABLE IF NOT EXISTS admin_ui_access_audit_entry(
    username VARCHAR(128),
    router_method_name VARCHAR(128),
    timestamp DATETIME(6) DEFAULT CURRENT_TIMESTAMP,
    details MEDIUMBLOB,
    PRIMARY KEY (username, timestamp),
    FOREIGN KEY (username) REFERENCES grr_users (username)
)""", """
CREATE INDEX IF NOT EXISTS timestamp_idx
ON admin_ui_access_audit_entry(timestamp)
""", """
CREATE INDEX IF NOT EXISTS router_method_name_idx
ON admin_ui_access_audit_entry(router_method_name)
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
