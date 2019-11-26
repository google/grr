-- `approval_request`


ALTER TABLE approval_request
  DROP FOREIGN KEY
    approval_request_ibfk_1;

ALTER TABLE approval_request
  ADD CONSTRAINT
    fk_approval_request_grr_users_username_hash
  FOREIGN KEY
    (username_hash)
  REFERENCES
    grr_users
    (username_hash)
  ON DELETE CASCADE;



-- `approval_grant`


ALTER TABLE approval_grant
  DROP FOREIGN KEY
    approval_grant_ibfk_1;

ALTER TABLE approval_grant
  ADD CONSTRAINT
    fk_approval_grant_approval_request
  FOREIGN KEY
    (username_hash, approval_id)
  REFERENCES
    approval_request
    (username_hash, approval_id)
  ON DELETE CASCADE;


ALTER TABLE approval_grant
  DROP FOREIGN KEY
    approval_grant_ibfk_2;

ALTER TABLE approval_grant
  ADD CONSTRAINT
    fk_approval_grant_grr_users_username_hash
  FOREIGN KEY
    (username_hash)
  REFERENCES
    grr_users
    (username_hash)
  ON DELETE CASCADE;


ALTER TABLE approval_grant
  DROP FOREIGN KEY
    approval_grant_ibfk_3;

ALTER TABLE approval_grant
  DROP INDEX
    grantor_username_hash;

ALTER TABLE approval_grant
  ADD CONSTRAINT
    fk_approval_grant_grr_users_grantor_username_hash
  FOREIGN KEY
    (grantor_username_hash)
  REFERENCES
    grr_users
    (username_hash)
  ON DELETE CASCADE;



-- `clients`


ALTER TABLE clients
  DROP FOREIGN KEY
    clients_ibfk_1;

ALTER TABLE clients
  DROP INDEX
    client_id;

ALTER TABLE clients
  ADD CONSTRAINT
    fk_clients_client_snapshot_history
  FOREIGN KEY
    (client_id, last_snapshot_timestamp)
  REFERENCES
    client_snapshot_history
    (client_id, timestamp);


ALTER TABLE clients
  DROP FOREIGN KEY
    clients_ibfk_2;

ALTER TABLE clients
  DROP INDEX
    client_id_2;

ALTER TABLE clients
  ADD CONSTRAINT
    fk_clients_client_startup_history
  FOREIGN KEY
    (client_id, last_startup_timestamp)
  REFERENCES
    client_startup_history
    (client_id, timestamp);


ALTER TABLE clients
  DROP FOREIGN KEY
    clients_ibfk_3;

ALTER TABLE clients
  DROP INDEX
    client_id_3;

ALTER TABLE clients
  ADD CONSTRAINT
    fk_clients_client_crash_history
  FOREIGN KEY
    (client_id, last_crash_timestamp)
  REFERENCES
    client_crash_history
    (client_id, timestamp);



-- `client_action_requests`


ALTER TABLE client_action_requests
  DROP FOREIGN KEY
    client_action_requests_ibfk_1;

ALTER TABLE client_action_requests
  ADD CONSTRAINT
    fk_client_action_requests_flow_requests
  FOREIGN KEY
    (client_id, flow_id, request_id)
  REFERENCES
    flow_requests
    (client_id, flow_id, request_id)
  ON DELETE CASCADE;



-- `client_snapshot_history`


ALTER TABLE client_snapshot_history
  DROP FOREIGN KEY
    client_snapshot_history_ibfk_1;

ALTER TABLE client_snapshot_history
  ADD CONSTRAINT
    fk_client_snapshot_history_clients
  FOREIGN KEY
    (client_id)
  REFERENCES
    clients
    (client_id)
  ON DELETE CASCADE;



-- `client_startup_history`


ALTER TABLE client_startup_history
  DROP FOREIGN KEY
    client_startup_history_ibfk_1;

ALTER TABLE client_startup_history
  ADD CONSTRAINT
    fk_client_startup_history_clients
  FOREIGN KEY
    (client_id)
  REFERENCES
    clients
    (client_id)
  ON DELETE CASCADE;



-- `client_crash_history`


ALTER TABLE client_crash_history
  DROP FOREIGN KEY
    client_crash_history_ibfk_1;

ALTER TABLE client_crash_history
  ADD CONSTRAINT
    fk_client_crash_history_clients
  FOREIGN KEY
    (client_id)
  REFERENCES
    clients
    (client_id)
  ON DELETE CASCADE;



-- `client_keywords`


ALTER TABLE client_keywords
  DROP FOREIGN KEY
    client_keywords_ibfk_1;

ALTER TABLE client_keywords
  ADD CONSTRAINT
    fk_client_keywords_clients
  FOREIGN KEY
    (client_id)
  REFERENCES
    clients
    (client_id)
  ON DELETE CASCADE;



-- `client_labels`


ALTER TABLE client_labels
  DROP FOREIGN KEY
    client_labels_ibfk_1;

ALTER TABLE client_labels
  ADD CONSTRAINT
    fk_client_labels_clients
  FOREIGN KEY
    (client_id)
  REFERENCES
    clients
    (client_id)
  ON DELETE CASCADE;



-- `client_stats`


ALTER TABLE client_stats
  DROP FOREIGN KEY
    client_stats_ibfk_1;

ALTER TABLE client_stats
  DROP INDEX
    client_id;

ALTER TABLE client_stats
  ADD CONSTRAINT
    fk_client_stats_clients
  FOREIGN KEY
    (client_id)
  REFERENCES
    clients
    (client_id)
  ON DELETE CASCADE;



-- `client_paths`


ALTER TABLE client_paths
  DROP FOREIGN KEY
    client_paths_ibfk_1;

ALTER TABLE client_paths
  ADD CONSTRAINT
    fk_client_paths_clients
  FOREIGN KEY
    (client_id)
  REFERENCES
    clients
    (client_id)
  ON DELETE CASCADE;


ALTER TABLE client_paths
  DROP FOREIGN KEY
    client_paths_ibfk_2;

ALTER TABLE client_paths
  DROP INDEX
    client_id;

ALTER TABLE client_paths
  ADD CONSTRAINT
    fk_client_paths_client_path_stat_entries
  FOREIGN KEY
    (client_id, path_type, path_id, last_stat_entry_timestamp)
  REFERENCES
    client_path_stat_entries
    (client_id, path_type, path_id, timestamp);


ALTER TABLE client_paths
  DROP FOREIGN KEY
    client_paths_ibfk_3;

ALTER TABLE client_paths
  DROP INDEX
    client_id_2;

ALTER TABLE client_paths
  ADD CONSTRAINT
    fk_client_paths_client_path_hash_entries
  FOREIGN KEY
    (client_id, path_type, path_id, last_hash_entry_timestamp)
  REFERENCES
    client_path_hash_entries
    (client_id, path_type, path_id, timestamp);



-- `client_path_stat_entries`


ALTER TABLE client_path_stat_entries
  DROP FOREIGN KEY
    client_path_stat_entries_ibfk_1;

ALTER TABLE client_path_stat_entries
  ADD CONSTRAINT
    fk_client_path_stat_entries_client_paths
  FOREIGN KEY
    (client_id, path_type, path_id)
  REFERENCES
    client_paths
    (client_id, path_type, path_id)
  ON DELETE CASCADE;



-- `client_path_hash_entries`


ALTER TABLE client_path_hash_entries
  DROP FOREIGN KEY
    client_path_hash_entries_ibfk_1;

ALTER TABLE client_path_hash_entries
  ADD CONSTRAINT
    fk_client_path_hash_entries_client_paths
  FOREIGN KEY
    (client_id, path_type, path_id)
  REFERENCES
    client_paths
    (client_id, path_type, path_id)
  ON DELETE CASCADE;



-- `cron_job_runs`


ALTER TABLE cron_job_runs
  DROP FOREIGN KEY
    cron_job_runs_ibfk_1;

ALTER TABLE cron_job_runs
  ADD CONSTRAINT
    fk_cron_job_runs_cron_jobs
  FOREIGN KEY
    (job_id)
  REFERENCES
    cron_jobs
    (job_id)
  ON DELETE CASCADE;



-- `flows`



ALTER TABLE flows
  DROP FOREIGN KEY
    flows_ibfk_1;

ALTER TABLE flows
  ADD CONSTRAINT
    fk_flows_clients
  FOREIGN KEY
    (client_id)
  REFERENCES
    clients
    (client_id)
  ON DELETE CASCADE;



-- `flow_requests`


ALTER TABLE flow_requests
  DROP FOREIGN KEY
    flow_requests_ibfk_1;

ALTER TABLE flow_requests
  ADD CONSTRAINT
    fk_flow_requests_clients
  FOREIGN KEY
    (client_id)
  REFERENCES
    clients
    (client_id)
  ON DELETE CASCADE;


ALTER TABLE flow_requests
  DROP FOREIGN KEY
    flow_requests_ibfk_2;

ALTER TABLE flow_requests
  ADD CONSTRAINT
    fk_flow_requests_flows
  FOREIGN KEY
    (client_id, flow_id)
  REFERENCES
    flows
    (client_id, flow_id)
  ON DELETE CASCADE;



-- `flow_processing_requests`


ALTER TABLE flow_processing_requests
  DROP FOREIGN KEY
    flow_processing_requests_ibfk_1;

ALTER TABLE flow_processing_requests
  ADD CONSTRAINT
    fk_flow_processing_requests_clients
  FOREIGN KEY
    (client_id)
  REFERENCES
    clients
    (client_id)
  ON DELETE CASCADE;


ALTER TABLE flow_processing_requests
  DROP FOREIGN KEY
    flow_processing_requests_ibfk_2;

ALTER TABLE flow_processing_requests
  ADD CONSTRAINT
    fk_flow_processing_requests_flows
  FOREIGN KEY
    (client_id, flow_id)
  REFERENCES
    flows
    (client_id, flow_id)
  ON DELETE CASCADE;



-- `flow_responses`


ALTER TABLE flow_responses
  DROP FOREIGN KEY
    flow_responses_ibfk_1;

ALTER TABLE flow_responses
  ADD CONSTRAINT
    fk_flow_responses_clients
  FOREIGN KEY
    (client_id)
  REFERENCES
    clients
    (client_id)
  ON DELETE CASCADE;


ALTER TABLE flow_responses
  DROP FOREIGN KEY
    flow_responses_ibfk_2;

ALTER TABLE flow_responses
  ADD CONSTRAINT
    fk_flow_responses_flow_requests
  FOREIGN KEY
    (client_id, flow_id, request_id)
  REFERENCES
    flow_requests
    (client_id, flow_id, request_id)
  ON DELETE CASCADE;



-- `flow_results`


ALTER TABLE flow_results
  DROP FOREIGN KEY
    flow_results_ibfk_1;

ALTER TABLE flow_results
  ADD CONSTRAINT
    fk_flow_results_clients
  FOREIGN KEY
    (client_id)
  REFERENCES
    clients
    (client_id)
  ON DELETE CASCADE;


ALTER TABLE flow_results
  DROP FOREIGN KEY
    flow_results_ibfk_2;

ALTER TABLE flow_results
  ADD CONSTRAINT
    fk_flow_results_flows
  FOREIGN KEY
    (client_id, flow_id)
  REFERENCES
    flows
    (client_id, flow_id)
  ON DELETE CASCADE;


-- `flow_log_entries`


ALTER TABLE flow_log_entries
  DROP FOREIGN KEY
    flow_log_entries_ibfk_1;

ALTER TABLE flow_log_entries
  ADD CONSTRAINT
    fk_flow_log_entries_clients
  FOREIGN KEY
    (client_id)
  REFERENCES
    clients
    (client_id)
  ON DELETE CASCADE;


ALTER TABLE flow_log_entries
  DROP FOREIGN KEY
    flow_log_entries_ibfk_2;

ALTER TABLE flow_log_entries
  ADD CONSTRAINT
    fk_flow_log_entries_flows
  FOREIGN KEY
    (client_id, flow_id)
  REFERENCES
    flows
    (client_id, flow_id)
  ON DELETE CASCADE;



-- `flow_output_plugin_log_entries`


ALTER TABLE flow_output_plugin_log_entries
  DROP FOREIGN KEY
    flow_output_plugin_log_entries_ibfk_1;

ALTER TABLE flow_output_plugin_log_entries
  ADD CONSTRAINT
    fk_flow_output_plugin_log_entries_clients
  FOREIGN KEY
    (client_id)
  REFERENCES
    clients
    (client_id)
  ON DELETE CASCADE;


ALTER TABLE flow_output_plugin_log_entries
  DROP FOREIGN KEY
    flow_output_plugin_log_entries_ibfk_2;

ALTER TABLE flow_output_plugin_log_entries
  ADD CONSTRAINT
    fk_flow_output_plugin_log_entries_flows
  FOREIGN KEY
    (client_id, flow_id)
  REFERENCES
    flows
    (client_id, flow_id)
  ON DELETE CASCADE;



-- `hunt_output_plugins_states`


ALTER TABLE hunt_output_plugins_states
  DROP FOREIGN KEY
    hunt_output_plugins_states_ibfk_1;

ALTER TABLE hunt_output_plugins_states
  ADD CONSTRAINT
    fk_hunt_output_plugins_states_hunts
  FOREIGN KEY
    (hunt_id)
  REFERENCES
    hunts
    (hunt_id)
  ON DELETE CASCADE;



-- `user_notification`


ALTER TABLE user_notification
  DROP FOREIGN KEY
    user_notification_ibfk_1;

ALTER TABLE user_notification
  ADD CONSTRAINT
    fk_user_notification_grr_users
  FOREIGN KEY
    (username_hash)
  REFERENCES
    grr_users
    (username_hash)
  ON DELETE CASCADE;
