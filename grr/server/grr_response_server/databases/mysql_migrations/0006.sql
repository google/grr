CREATE TABLE `flow_errors` (
  `error_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `client_id` BIGINT UNSIGNED DEFAULT NULL,
  `flow_id` BIGINT UNSIGNED DEFAULT NULL,
  `hunt_id` BIGINT UNSIGNED DEFAULT NULL,
  `timestamp` TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `payload` MEDIUMBLOB,
  `type` VARCHAR(128) DEFAULT NULL,
  `tag` VARCHAR(128) DEFAULT NULL,
  PRIMARY KEY (`error_id`),
  KEY `flow_errors_by_client_id_flow_id_timestamp`
    (`client_id`,`flow_id`,`timestamp`),
  KEY `flow_errors_hunt_id_flow_id_timestamp`
    (`hunt_id`,`flow_id`,`timestamp`),
  KEY `flow_errors_hunt_id_flow_id_type_tag_timestamp`
    (`hunt_id`,`flow_id`,`type`,`tag`,`timestamp`),
  CONSTRAINT `fk_flow_errors_clients`
    FOREIGN KEY (`client_id`)
    REFERENCES `clients` (`client_id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_flow_errors_flows`
    FOREIGN KEY (`client_id`, `flow_id`)
    REFERENCES `flows` (`client_id`, `flow_id`)
    ON DELETE CASCADE
);
