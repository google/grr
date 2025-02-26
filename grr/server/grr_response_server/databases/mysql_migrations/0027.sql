CREATE TABLE `signed_commands`(
  `id` VARCHAR(128) NOT NULL,
  `operating_system` INT(8) NOT NULL,
  `ed25519_signature` BINARY(64) NOT NULL,
  `path` TEXT NOT NULL,
  `args` TEXT,
  `unsigned_stdin` BOOL,
  `signed_stdin` LONGBLOB,
  PRIMARY KEY(`id`, `operating_system`));

CREATE TABLE `signed_command_env_vars`(
  `id` VARCHAR(128) NOT NULL,
  `operating_system` INT(8) NOT NULL,
  `name` VARCHAR(128) NOT NULL,
  `value` VARCHAR(128) NOT NULL,
  PRIMARY KEY(`id`, `operating_system`, `name`),
  CONSTRAINT `fk_signed_command_env_vars_signed_commands`
  FOREIGN KEY(`id`, `operating_system`)
  REFERENCES `signed_commands`(`id`, `operating_system`)
  ON DELETE CASCADE);

CREATE TABLE `signed_command_args`(
  `id` VARCHAR(128) NOT NULL,
  `operating_system` INT(8) NOT NULL,
  `arg` VARCHAR(128) NOT NULL,
  `position` INT(8) NOT NULL,
  PRIMARY KEY(`id`, `operating_system`, `arg`),
  CONSTRAINT `fk_signed_command_args_signed_commands`
  FOREIGN KEY(`id`, `operating_system`)
  REFERENCES `signed_commands`(`id`, `operating_system`)
  ON DELETE CASCADE)
