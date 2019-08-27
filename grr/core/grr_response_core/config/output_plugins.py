#!/usr/bin/env python
"""Configuration parameters for server output plugins."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import config_lib
from grr_response_core.lib import rdfvalue

config_lib.DEFINE_string("BigQuery.service_acct_json", None,
                         "The json contents of the service account file.")

config_lib.DEFINE_string("BigQuery.project_id", None,
                         "The BigQuery project_id.")

config_lib.DEFINE_string("BigQuery.dataset_id", "grr",
                         "The BigQuery project_id.")

config_lib.DEFINE_integer("BigQuery.max_file_post_size", 5 * 1000 * 1000,
                          "Max size of file to put in each POST "
                          "to bigquery. Note enforcement is not exact.")

config_lib.DEFINE_integer("BigQuery.retry_max_attempts", 2,
                          "Total number of times to retry an upload.")

config_lib.DEFINE_integer("BigQuery.max_upload_failures", 100,
                          "Total number of times to try uploading to BigQuery"
                          " for a given hunt or flow.")

config_lib.DEFINE_semantic_value(rdfvalue.Duration, "BigQuery.retry_interval",
                                 "2s", "Time to wait before first retry.")

config_lib.DEFINE_integer("BigQuery.retry_multiplier", 2,
                          "For each retry, multiply last delay by this value.")

config_lib.DEFINE_integer_list("BigQuery.retry_status_codes",
                               [404, 500, 502, 503, 504],
                               "HTTP status codes on which we should retry.")
