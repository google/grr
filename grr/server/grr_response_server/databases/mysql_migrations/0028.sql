CREATE TABLE `flow_rrg_logs` (
  `client_id` BIGINT UNSIGNED NOT NULL,
  `flow_id` BIGINT UNSIGNED NOT NULL,
  `request_id` BIGINT UNSIGNED NOT NULL,
  `response_id` BIGINT UNSIGNED NOT NULL,

  `log_level` INT UNSIGNED NOT NULL,
  `log_time` TIMESTAMP(6) NOT NULL,
  `log_message` TEXT NOT NULL,

  `timestamp` TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

  PRIMARY KEY (`client_id`, `flow_id`, `request_id`, `response_id`),

  CONSTRAINT `fk_flow_rrg_logs_clients`
    FOREIGN KEY (`client_id`)
    REFERENCES `clients` (`client_id`)
    ON DELETE CASCADE,

  CONSTRAINT `fk_flow_rrg_logs_flows`
    FOREIGN KEY (`client_id`, `flow_id`)
    REFERENCES `flows` (`client_id`, `flow_id`)
    ON DELETE CASCADE
);
