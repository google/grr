#!/usr/bin/env python
"""Cron job to process hunt results."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging


from future.utils import iteritems
from future.utils import itervalues

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.util import collection
from grr_response_core.stats import stats_collector_instance
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import output_plugin
from grr_response_server.aff4_objects import cronjobs
from grr_response_server.hunts import implementation
from grr_response_server.hunts import results as hunts_results


class ResultsProcessingError(Exception):
  """This exception is raised when errors happen during results processing."""

  def __init__(self):
    self.exceptions_by_hunt = {}
    super(ResultsProcessingError, self).__init__()

  def RegisterSubException(self, hunt_urn, plugin_name, exception):
    self.exceptions_by_hunt.setdefault(hunt_urn, {}).setdefault(
        plugin_name, []).append(exception)

  def __repr__(self):
    messages = []
    for hunt_urn, exceptions_by_plugin in iteritems(self.exceptions_by_hunt):
      for plugin_name, exception in iteritems(exceptions_by_plugin):
        messages.append("Exception for hunt %s (plugin %s): %s" %
                        (hunt_urn, plugin_name, exception))

    return "\n".join(messages)


@cronjobs.DualDBSystemCronJob(
    legacy_name="ProcessHuntResultCollectionsCronFlow", stateful=False)
class ProcessHuntResultCollectionsCronJob(object):
  """Periodic cron flow that processes hunt results.

  The ProcessHuntResultCollectionsCronFlow reads hunt results stored in
  HuntResultCollections and feeds runs output plugins on them.
  """

  frequency = rdfvalue.Duration("5m")
  lifetime = rdfvalue.Duration("40m")
  allow_overruns = True

  BATCH_SIZE = 5000

  def CheckIfRunningTooLong(self):
    """Return True if the cron job's time is expired."""

    if self.max_running_time:
      elapsed = rdfvalue.RDFDatetime.Now() - self.start_time
      if elapsed > self.max_running_time:
        return True
    return False

  def LoadPlugins(self, hunt_urn, metadata_obj):
    """Loads plugins from given hunt metadata object."""

    output_plugins = metadata_obj.Get(metadata_obj.Schema.OUTPUT_PLUGINS)
    if not output_plugins:
      return output_plugins, []

    output_plugins = output_plugins.ToDict()
    used_plugins = []
    unused_plugins = []

    for plugin_def, state in itervalues(output_plugins):
      plugin_cls = plugin_def.GetPluginClass()
      plugin_obj = plugin_cls(
          source_urn=rdfvalue.RDFURN(hunt_urn).Add("Results"),
          args=plugin_def.plugin_args,
          token=metadata_obj.token)
      used_plugins.append((plugin_def, plugin_obj, state))
    return output_plugins, used_plugins

  def RunPlugins(self, hunt_urn, plugins, results, exceptions_by_plugin):
    """Runs given plugins on a given hunt."""

    for plugin_def, plugin, plugin_state in plugins:
      try:
        plugin.ProcessResponses(plugin_state, results)
        plugin.Flush(plugin_state)
        plugin.UpdateState(plugin_state)

        plugin_status = output_plugin.OutputPluginBatchProcessingStatus(
            plugin_descriptor=plugin_def,
            status="SUCCESS",
            batch_size=len(results))
        stats_collector_instance.Get().IncrementCounter(
            "hunt_results_ran_through_plugin",
            delta=len(results),
            fields=[plugin_def.plugin_name])

      except Exception as e:  # pylint: disable=broad-except
        logging.exception(
            "Error processing hunt results: hunt %s, "
            "plugin %s", hunt_urn, utils.SmartStr(plugin))
        self.Log("Error processing hunt results (hunt %s, "
                 "plugin %s): %s" % (hunt_urn, utils.SmartStr(plugin), e))
        stats_collector_instance.Get().IncrementCounter(
            "hunt_output_plugin_errors", fields=[plugin_def.plugin_name])

        plugin_status = output_plugin.OutputPluginBatchProcessingStatus(
            plugin_descriptor=plugin_def,
            status="ERROR",
            summary=utils.SmartStr(e),
            batch_size=len(results))
        exceptions_by_plugin.setdefault(plugin_def, []).append(e)

      with data_store.DB.GetMutationPool() as pool:
        implementation.GRRHunt.PluginStatusCollectionForHID(hunt_urn).Add(
            plugin_status, mutation_pool=pool)
        if plugin_status.status == plugin_status.Status.ERROR:
          implementation.GRRHunt.PluginErrorCollectionForHID(hunt_urn).Add(
              plugin_status, mutation_pool=pool)

  def ProcessOneHunt(self, exceptions_by_hunt):
    """Reads results for one hunt and process them."""
    hunt_results_urn, results = (
        hunts_results.HuntResultQueue.ClaimNotificationsForCollection(
            token=self.token, lease_time=self.lifetime))
    logging.debug("Found %d results for hunt %s", len(results),
                  hunt_results_urn)
    if not results:
      return 0

    hunt_urn = rdfvalue.RDFURN(hunt_results_urn.Dirname())
    batch_size = self.BATCH_SIZE
    metadata_urn = hunt_urn.Add("ResultsMetadata")
    exceptions_by_plugin = {}
    num_processed_for_hunt = 0
    collection_obj = implementation.GRRHunt.ResultCollectionForHID(hunt_urn)
    try:
      with aff4.FACTORY.OpenWithLock(
          metadata_urn, lease_time=600, token=self.token) as metadata_obj:
        all_plugins, used_plugins = self.LoadPlugins(hunt_urn, metadata_obj)
        num_processed = int(
            metadata_obj.Get(metadata_obj.Schema.NUM_PROCESSED_RESULTS))
        for batch in collection.Batch(results, batch_size):
          results = list(
              collection_obj.MultiResolve(
                  [r.value.ResultRecord() for r in batch]))
          self.RunPlugins(hunt_urn, used_plugins, results, exceptions_by_plugin)

          hunts_results.HuntResultQueue.DeleteNotifications(
              batch, token=self.token)
          num_processed += len(batch)
          num_processed_for_hunt += len(batch)
          self.HeartBeat()
          metadata_obj.Set(
              metadata_obj.Schema.NUM_PROCESSED_RESULTS(num_processed))
          metadata_obj.UpdateLease(600)
          if self.CheckIfRunningTooLong():
            logging.warning("Run too long, stopping.")
            break

        metadata_obj.Set(metadata_obj.Schema.OUTPUT_PLUGINS(all_plugins))
        metadata_obj.Set(
            metadata_obj.Schema.NUM_PROCESSED_RESULTS(num_processed))
    except aff4.LockError:
      logging.warn(
          "ProcessHuntResultCollectionsCronFlow: "
          "Could not get lock on hunt metadata %s.", metadata_urn)
      return 0

    if exceptions_by_plugin:
      for plugin, exceptions in iteritems(exceptions_by_plugin):
        exceptions_by_hunt.setdefault(hunt_urn, {}).setdefault(
            plugin, []).extend(exceptions)

    logging.debug("Processed %d results.", num_processed_for_hunt)
    return len(results)

  def Run(self):
    """Run this cron job."""
    self.start_time = rdfvalue.RDFDatetime.Now()

    exceptions_by_hunt = {}
    self.max_running_time = self.lifetime * 0.6

    while not self.CheckIfRunningTooLong():
      count = self.ProcessOneHunt(exceptions_by_hunt)
      if not count:
        break

    if exceptions_by_hunt:
      e = ResultsProcessingError()
      for hunt_urn, exceptions_by_plugin in iteritems(exceptions_by_hunt):
        for plugin, exceptions in iteritems(exceptions_by_plugin):
          for exception in exceptions:
            e.RegisterSubException(hunt_urn, plugin, exception)
      raise e
