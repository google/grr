ALTER TABLE flow_requests
  ADD COLUMN next_response_id BIGINT UNSIGNED;

ALTER TABLE flow_requests
  ADD COLUMN callback_state VARCHAR(128) DEFAULT NULL;
