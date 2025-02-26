ALTER TABLE signed_commands
  ADD COLUMN command MEDIUMBLOB NOT NULL DEFAULT '',
  DROP COLUMN `path`,
  DROP COLUMN `args`,
  DROP COLUMN `unsigned_stdin`,
  DROP COLUMN `signed_stdin`;

DROP TABLE `signed_command_args`;
DROP TABLE `signed_command_env_vars`;
