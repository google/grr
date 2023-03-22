-- Trigger an update of `client_paths.last_stat_entry_timestamp` after a
-- new recored is inserted into `client_path_stat_entries`.
CREATE
  TRIGGER
    client_paths_last_stat_entry_timestamp_insert
      AFTER INSERT
ON
  client_path_stat_entries
    FOR EACH ROW UPDATE client_paths
SET
  -- Note: using a conditional update here is more efficient than
  -- restricting the UPDATE query via its WHERE clause, as it allows
  -- finer-grained locking to be used (i.e. row locking based on the primary
  -- key matching in the WHERE clause).
  last_stat_entry_timestamp = IF(
    last_stat_entry_timestamp IS NULL OR last_stat_entry_timestamp < NEW.timestamp,
    NEW.timestamp,
    last_stat_entry_timestamp)
WHERE (client_id, path_type, path_id) = (NEW.client_id, NEW.path_type, NEW.path_id);

-- Trigger an update of `client_paths.last_stat_entry_timestamp` after a
-- record is updated in `client_path_stat_entries`.
CREATE
  TRIGGER
    client_paths_last_stat_entry_timestamp_update
      AFTER UPDATE
ON
  client_path_stat_entries
    FOR EACH ROW UPDATE client_paths
SET
  -- Note: using a conditional update here is more efficient than
  -- restricting the UPDATE query via its WHERE clause, as it allows
  -- finer-grained locking to be used (i.e. row locking based on the primary
  -- key matching in the WHERE clause).
  last_stat_entry_timestamp = IF(
    last_stat_entry_timestamp IS NULL OR last_stat_entry_timestamp < NEW.timestamp,
    NEW.timestamp,
    last_stat_entry_timestamp)
WHERE (client_id, path_type, path_id) = (NEW.client_id, NEW.path_type, NEW.path_id);

-- Trigger an update of `client_paths.last_hash_entry_timestamp` after a
-- new recored is inserted into `client_path_hash_entries`.
CREATE
  TRIGGER
    client_paths_last_hash_entry_timestamp_insert
      AFTER INSERT
ON
  client_path_hash_entries
    FOR EACH ROW UPDATE client_paths
SET
  -- Note: using a conditional update here is more efficient than
  -- restricting the UPDATE query via its WHERE clause, as it allows
  -- finer-grained locking to be used (i.e. row locking based on the primary
  -- key matching in the WHERE clause).
  last_hash_entry_timestamp = IF(
    last_hash_entry_timestamp IS NULL OR last_hash_entry_timestamp < NEW.timestamp,
    NEW.timestamp,
    last_hash_entry_timestamp)
WHERE (client_id, path_type, path_id) = (NEW.client_id, NEW.path_type, NEW.path_id);

-- Trigger an update of `client_paths.last_hash_entry_timestamp` after a
-- record is updated in `client_path_hash_entries`.
CREATE
  TRIGGER
    client_paths_last_hash_entry_timestamp_update
      AFTER UPDATE
ON
  client_path_hash_entries
    FOR EACH ROW UPDATE client_paths
SET
  -- Note: using a conditional update here is more efficient than
  -- restricting the UPDATE query via its WHERE clause, as it allows
  -- finer-grained locking to be used (i.e. row locking based on the primary
  -- key matching in the WHERE clause).
  last_hash_entry_timestamp = IF(
    last_hash_entry_timestamp IS NULL OR last_hash_entry_timestamp < NEW.timestamp,
    NEW.timestamp,
    last_hash_entry_timestamp)
WHERE (client_id, path_type, path_id) = (NEW.client_id, NEW.path_type, NEW.path_id);
