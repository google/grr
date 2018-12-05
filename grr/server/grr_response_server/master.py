#!/usr/bin/env python
"""The master watcher class.

It often makes sense to have a backup instance of the GRR server
environment running. If you decide to do so, override this class with
functionality to determine if this instance is currently active
("Master") or not and store the result using the SetMaster
function. Note that you can have multiple Workers and
Frontend Servers running without any problems as long as you don't use
data store replication. Only if you work on a replicated database you
will run into race conditions and have to disable the backup instances.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging


from future.utils import with_metaclass

from grr_response_core import config
from grr_response_core.lib import registry
from grr_response_core.stats import stats_collector_instance


class DefaultMasterWatcher(with_metaclass(registry.MetaclassRegistry, object)):
  """A Master Watcher that always returns True."""

  is_master = True

  def __init__(self):
    super(DefaultMasterWatcher, self).__init__()
    self.SetMaster(True)

  def IsMaster(self):
    return self.is_master

  def SetMaster(self, master=True):
    """Switch the is_master stat variable."""

    if master:
      logging.info("data center is now active.")
      stats_collector_instance.Get().SetGaugeValue("is_master", 1)
      self.is_master = True
    else:
      logging.info("data center became inactive.")
      stats_collector_instance.Get().SetGaugeValue("is_master", 0)
      self.is_master = False


MASTER_WATCHER = None


class MasterInit(registry.InitHook):
  """Init hook class for the master watcher."""

  def RunOnce(self):
    global MASTER_WATCHER  # pylint: disable=global-statement

    watcher_name = config.CONFIG["Server.master_watcher_class"]
    watcher_cls = DefaultMasterWatcher.classes[watcher_name]

    MASTER_WATCHER = watcher_cls()
