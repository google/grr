CREATE TABLE `blob_encryption_keys` (
  -- A unique identifier of the blob.
  `blob_id` BINARY(32) NOT NULL,
  -- A timestamp at which the association was created.
  `timestamp` TIMESTAMP(6) NOT NULL DEFAULT NOW(6),
  -- A unique identifier of the key.
  `key_id` VARCHAR(256) NOT NULL,
  -- A random 96-bit initialization vector used for encryption.
  `nonce` BINARY(12) NOT NULL,

  PRIMARY KEY (`blob_id`, `timestamp`)
);
