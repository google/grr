ALTER TABLE client_paths
  DROP FOREIGN KEY
    fk_client_paths_client_path_stat_entries;

ALTER TABLE client_paths
  ADD FOREIGN KEY
    fk_client_paths_client_path_stat_entries
    (client_id, path_type, path_id, last_stat_entry_timestamp)
  REFERENCES
    client_path_stat_entries(client_id, path_type, path_id, timestamp)
  ON DELETE CASCADE;


ALTER TABLE client_paths
  DROP FOREIGN KEY
    fk_client_paths_client_path_hash_entries;

ALTER TABLE client_paths
  ADD FOREIGN KEY
    fk_client_paths_client_path_hash_entries
    (client_id, path_type, path_id, last_hash_entry_timestamp)
  REFERENCES
    client_path_hash_entries(client_id, path_type, path_id, timestamp)
  ON DELETE CASCADE;
