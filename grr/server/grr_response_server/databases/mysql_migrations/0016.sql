-- Drop VFS stat/hash timestamp update triggers.
-- They are no longer needed, since
-- `client_paths.last_{stat,hash}_entry_timestamp have been removed.
DROP TRIGGER IF EXISTS client_paths_last_stat_entry_timestamp_insert;
DROP TRIGGER IF EXISTS client_paths_last_stat_entry_timestamp_update;
DROP TRIGGER IF EXISTS client_paths_last_hash_entry_timestamp_insert;
DROP TRIGGER IF EXISTS client_paths_last_hash_entry_timestamp_update;

-- Drop the FK constraint that links `client_paths.last_stat_entry_timestamp`
-- to `client_path_stat_entries.timestamp`, so that we can drop the
-- `last_stat_entry_timestamp` column.
-- Note: since the initial constraint was created with a default name, and
-- MariaDB and MySQL assign different default names to constraints, we'll
-- need to fetch the constraint name from `INFORMATION_SCHEMA`, so that
-- this works with both SQL flavors.
SET @cstr_name = (
  SELECT CONSTRAINT_NAME
  FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
  WHERE
    TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = "client_paths"
    AND COLUMN_NAME = "last_stat_entry_timestamp"
    AND REFERENCED_TABLE_NAME = "client_path_stat_entries"
    AND REFERENCED_COLUMN_NAME = "timestamp"
    AND ORDINAL_POSITION = 4
);

SET @query = CONCAT("ALTER TABLE client_paths DROP FOREIGN KEY ", @cstr_name);

PREPARE stmt FROM @query;

EXECUTE stmt;

ALTER TABLE client_paths
DROP INDEX fk_client_paths_client_path_stat_entries;

-- See the above comment on dropping the FK constraint for
-- `client_paths.last_stat_entry_timestamp`.
-- The same applies for `client_paths.last_hash_entry_timestamp`.
SET @cstr_name = (
  SELECT CONSTRAINT_NAME
  FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
  WHERE
    TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = "client_paths"
    AND COLUMN_NAME = "last_hash_entry_timestamp"
    AND REFERENCED_TABLE_NAME = "client_path_hash_entries"
    AND REFERENCED_COLUMN_NAME = "timestamp"
    AND ORDINAL_POSITION = 4
);

SET @query = CONCAT("ALTER TABLE client_paths DROP FOREIGN KEY ", @cstr_name);

PREPARE stmt FROM @query;

EXECUTE stmt;

ALTER TABLE client_paths
DROP INDEX fk_client_paths_client_path_hash_entries;

-- Drop `client_paths.last_{stat,hash}_entry_timestamp
ALTER TABLE client_paths
DROP COLUMN last_stat_entry_timestamp,
DROP COLUMN last_hash_entry_timestamp;
