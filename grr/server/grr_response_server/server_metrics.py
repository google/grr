#!/usr/bin/env python
"""Definitions for stats metrics used by GRR server components."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from builtins import range  # pylint: disable=redefined-builtin

from grr_response_core.stats import stats_utils


def GetMetadata():
  """Returns a list of MetricMetadata for GRR server components."""
  return [
      # GRR user-management metrics.
      stats_utils.CreateEventMetadata(
          "acl_check_time", fields=[("check_type", str)]),
      stats_utils.CreateCounterMetadata(
          "approval_searches",
          fields=[("reason_presence", str), ("source", str)]),

      # Cronjob metrics.
      stats_utils.CreateCounterMetadata("cron_internal_error"),
      stats_utils.CreateCounterMetadata(
          "cron_job_failure", fields=[("cron_job_id", str)]),
      stats_utils.CreateCounterMetadata(
          "cron_job_timeout", fields=[("cron_job_id", str)]),
      stats_utils.CreateEventMetadata(
          "cron_job_latency", fields=[("cron_job_id", str)]),

      # Access-control metrics.
      stats_utils.CreateCounterMetadata("grr_expired_tokens"),

      # Datastore metrics.
      stats_utils.CreateCounterMetadata("grr_commit_failure"),
      stats_utils.CreateCounterMetadata("datastore_retries"),
      stats_utils.CreateGaugeMetadata(
          "datastore_size",
          int,
          docstring="Size of data store in bytes",
          units="BYTES"),
      stats_utils.CreateCounterMetadata("grr_task_retransmission_count"),
      stats_utils.CreateCounterMetadata("grr_task_ttl_expired_count"),
      stats_utils.CreateEventMetadata(
          "db_request_latency",
          fields=[("call", str)],
          bins=[0.05 * 1.2**x for x in range(30)]),  # 50ms to ~10 secs
      stats_utils.CreateCounterMetadata(
          "db_request_errors", fields=[("call", str), ("type", str)]),

      # Threadpool metrics.
      stats_utils.CreateGaugeMetadata(
          "threadpool_outstanding_tasks", int, fields=[("pool_name", str)]),
      stats_utils.CreateGaugeMetadata(
          "threadpool_threads", int, fields=[("pool_name", str)]),
      stats_utils.CreateGaugeMetadata(
          "threadpool_cpu_use", float, fields=[("pool_name", str)]),
      stats_utils.CreateCounterMetadata(
          "threadpool_task_exceptions", fields=[("pool_name", str)]),
      stats_utils.CreateEventMetadata(
          "threadpool_working_time", fields=[("pool_name", str)]),
      stats_utils.CreateEventMetadata(
          "threadpool_queueing_time", fields=[("pool_name", str)]),

      # Worker and flow-related metrics.
      stats_utils.CreateCounterMetadata("grr_flows_stuck"),
      stats_utils.CreateCounterMetadata(
          "worker_bad_flow_objects", fields=[("type", str)]),
      stats_utils.CreateCounterMetadata(
          "worker_session_errors", fields=[("type", str)]),
      stats_utils.CreateCounterMetadata(
          "worker_flow_lock_error",
          docstring="Worker lock failures. We expect these to be high when the "
          "systemis idle."),
      stats_utils.CreateEventMetadata(
          "worker_flow_processing_time", fields=[("flow", str)]),
      stats_utils.CreateEventMetadata("worker_time_to_retrieve_notifications"),
      stats_utils.CreateCounterMetadata("grr_flow_completed_count"),
      stats_utils.CreateCounterMetadata("grr_flow_errors"),
      stats_utils.CreateCounterMetadata("grr_flow_invalid_flow_count"),
      stats_utils.CreateCounterMetadata("grr_request_retransmission_count"),
      stats_utils.CreateCounterMetadata("grr_response_out_of_order"),
      stats_utils.CreateCounterMetadata("grr_unique_clients"),
      stats_utils.CreateCounterMetadata("grr_worker_states_run"),
      stats_utils.CreateCounterMetadata("grr_well_known_flow_requests"),
      stats_utils.CreateCounterMetadata("flow_starts", fields=[("flow", str)]),
      stats_utils.CreateCounterMetadata("flow_errors", fields=[("flow", str)]),
      stats_utils.CreateCounterMetadata(
          "flow_completions", fields=[("flow", str)]),
      stats_utils.CreateCounterMetadata(
          "well_known_flow_requests", fields=[("flow", str)]),
      stats_utils.CreateCounterMetadata(
          "well_known_flow_errors", fields=[("flow", str)]),

      # Hunt-related metrics.
      stats_utils.CreateCounterMetadata(
          "hunt_output_plugin_verifications", fields=[("status", str)]),
      stats_utils.CreateCounterMetadata(
          "hunt_output_plugin_verification_errors"),
      stats_utils.CreateCounterMetadata(
          "hunt_output_plugin_errors", fields=[("plugin", str)]),
      stats_utils.CreateCounterMetadata(
          "hunt_results_ran_through_plugin", fields=[("plugin", str)]),
      stats_utils.CreateCounterMetadata("hunt_results_compacted"),
      stats_utils.CreateCounterMetadata(
          "hunt_results_compaction_locking_errors"),
      stats_utils.CreateCounterMetadata("hunt_results_added"),

      # Metric used to identify the master in a distributed server setup.
      stats_utils.CreateGaugeMetadata("is_master", int),

      # GRR-API metrics.
      stats_utils.CreateEventMetadata(
          "api_method_latency",
          fields=[("method_name", str), ("protocol", str), ("status", str)]),
      stats_utils.CreateEventMetadata(
          "api_access_probe_latency",
          fields=[("method_name", str), ("protocol", str), ("status", str)]),

      # Client-related metrics.
      stats_utils.CreateCounterMetadata("grr_client_crashes"),
      stats_utils.CreateCounterMetadata(
          "client_pings_by_label", fields=[("label", str)]),

      # Metrics specific to GRR frontends.
      stats_utils.CreateGaugeMetadata(
          "frontend_active_count", int, fields=[("source", str)]),
      stats_utils.CreateGaugeMetadata("frontend_max_active_count", int),
      stats_utils.CreateCounterMetadata(
          "frontend_http_requests", fields=[("action", str), ("protocol",
                                                              str)]),
      stats_utils.CreateCounterMetadata(
          "frontend_in_bytes", fields=[("source", str)]),
      stats_utils.CreateCounterMetadata(
          "frontend_out_bytes", fields=[("source", str)]),
      stats_utils.CreateCounterMetadata(
          "frontend_request_count", fields=[("source", str)]),
      stats_utils.CreateCounterMetadata(
          "frontend_inactive_request_count", fields=[("source", str)]),
      stats_utils.CreateEventMetadata(
          "frontend_request_latency", fields=[("source", str)]),
      stats_utils.CreateEventMetadata("grr_frontendserver_handle_time"),
      stats_utils.CreateCounterMetadata("grr_frontendserver_handle_num"),
      stats_utils.CreateGaugeMetadata("grr_frontendserver_client_cache_size",
                                      int),
      stats_utils.CreateCounterMetadata("grr_messages_sent"),
      stats_utils.CreateCounterMetadata(
          "grr_pub_key_cache", fields=[("type", str)]),
  ]
