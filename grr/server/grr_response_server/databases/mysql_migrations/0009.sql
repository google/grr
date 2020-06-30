CREATE TABLE `scheduled_flows` (
  `client_id` BIGINT UNSIGNED NOT NULL,
  `creator_username_hash` BINARY(32) NOT NULL,
  `scheduled_flow_id` BIGINT UNSIGNED NOT NULL,
  `flow_name` varchar(64) NOT NULL,
  `flow_args` LONGBLOB NOT NULL,
  `runner_args` LONGBLOB NOT NULL,
  `create_time` TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `error` TEXT DEFAULT NULL,
  PRIMARY KEY (`client_id`, `creator_username_hash`, `scheduled_flow_id`),
  CONSTRAINT `fk_scheduled_flows_clients`
    FOREIGN KEY (`client_id`)
    REFERENCES `clients` (`client_id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_scheduled_flows_grr_users`
    FOREIGN KEY (`creator_username_hash`)
    REFERENCES `grr_users` (`username_hash`)
    ON DELETE CASCADE
);
