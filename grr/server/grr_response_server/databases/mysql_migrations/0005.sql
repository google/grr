CREATE TABLE yara_signature_references(
    blob_id BINARY(32) NOT NULL PRIMARY KEY,
    username_hash BINARY(32) NOT NULL,
    timestamp TIMESTAMP(6) NOT NULL DEFAULT NOW(6)
);

ALTER TABLE yara_signature_references
  ADD CONSTRAINT
    fk_yara_signature_references_grr_users_username_hash
  FOREIGN KEY
    (username_hash)
  REFERENCES
    grr_users(username_hash)
  ON DELETE CASCADE;
