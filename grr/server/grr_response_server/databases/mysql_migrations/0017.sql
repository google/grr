CREATE TABLE `client_rrg_startup_history` (
  -- A unique identifier of the row.
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  -- A unique identifier of the client.
  `client_id` BIGINT UNSIGNED NOT NULL,
  -- A timestamp at which the startup record was written.
  `timestamp` TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  -- A serialized protobuf `rrg.startup.Startup` message with startup record.
  `startup` MEDIUMBLOB,

  PRIMARY KEY (`id`),

  CONSTRAINT `fk_client_rrg_startup_history_clients`
    FOREIGN KEY (`client_id`)
    REFERENCES `clients` (`client_id`)
    ON DELETE CASCADE
);
