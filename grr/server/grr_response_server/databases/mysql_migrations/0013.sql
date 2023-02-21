CREATE TABLE `blob_encryption_keys` (
  -- A unique identifier of the blob.
  `blob_id` BINARY(32) NOT NULL,
  -- A timestamp at which the association was created.
  `timestamp` TIMESTAMP(6) NOT NULL DEFAULT NOW(6),
  -- A unique name of the key.
  `key_name` VARCHAR(256) NOT NULL,

  PRIMARY KEY (`blob_id`, `timestamp`)
);
