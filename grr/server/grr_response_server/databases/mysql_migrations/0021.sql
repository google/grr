-- Drop default value for `clients.first_seen`.
ALTER TABLE clients MODIFY first_seen TIMESTAMP(6) NULL DEFAULT NULL;
