#!/usr/bin/env python
"""Configuration parameters for server output plugins."""


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

# SplunkOutputPlugin
config_lib.DEFINE_string(
    "Splunk.url", None, "Absolute URL of the Splunk installation, e.g. "
    "'https://mysplunkserver.example.com:8088'")

config_lib.DEFINE_bool(
    "Splunk.verify_https", True,
    "Verify the certificate for HTTPS connections. Setting this to False comes "
    "with big security risks. Instead, when using self-signed certificates, "
    "set REQUESTS_CA_BUNDLE environment variable to the path of the cert file. "
    "See https://requests.readthedocs.io/en/master/user/advanced/.")

config_lib.DEFINE_string(
    "Splunk.token", None,
    "Token used to authenticate with Splunk HTTP Event Collector.")

config_lib.DEFINE_string("Splunk.source", "grr",
                         "The source value assigned to all submitted events.")

config_lib.DEFINE_string(
    "Splunk.sourcetype", "grr_flow_result",
    "The sourcetype value assigned to all submitted events.")

config_lib.DEFINE_string("Splunk.index", None,
                         "The index assigned to all submitted events.")

# Elasticsearch Output Plugin
config_lib.DEFINE_string(
    "Elasticsearch.url", None, "Absolute URL of the Elasticsearch installation,"
    " e.g. 'https://myelasticsearch.example.com:9200'")

config_lib.DEFINE_string(
    "Elasticsearch.token", "",
    "Token used to authenticate with the Elasticsearch cluster.")

config_lib.DEFINE_bool(
    "Elasticsearch.verify_https", True,
    "Verify the certificate for HTTPS connections. Setting this to False comes "
    "with big security risks. Instead, when using self-signed certificates, "
    "set REQUESTS_CA_BUNDLE environment variable to the path of the cert file. "
    "See https://requests.readthedocs.io/en/master/user/advanced/.")

config_lib.DEFINE_string("Elasticsearch.index", "grr-flows",
                         "The index assigned to all submitted events.")

# WebhookOutputPlugin
config_lib.DEFINE_string(
    "Webhook.url", None, "Absolute URL of the HTTP Webhook, e.g. "
    "'https://mywebhookserver.example.com:8088'")

config_lib.DEFINE_bool(
    "Webhook.verify_https", True,
    "Verify the certificate for HTTPS connections. Setting this to False comes "
    "with big security risks. Instead, when using self-signed certificates, "
    "set REQUESTS_CA_BUNDLE environment variable to the path of the cert file. "
    "See https://requests.readthedocs.io/en/master/user/advanced/.")
