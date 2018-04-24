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


import logging


from grr import config
from grr.lib import registry
from grr.lib import stats


class DefaultMasterWatcher(object):
  """A Master Watcher that always returns True."""

  __metaclass__ = registry.MetaclassRegistry

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
      stats.STATS.SetGaugeValue("is_master", 1)
      self.is_master = True
    else:
      logging.info("data center became inactive.")
      stats.STATS.SetGaugeValue("is_master", 0)
      self.is_master = False


MASTER_WATCHER = None


class MasterInit(registry.InitHook):
  """Init hook class for the master watcher."""

  def RunOnce(self):
    # stat is set to 0 at registration time.
    stats.STATS.RegisterGaugeMetric("is_master", int)

    global MASTER_WATCHER  # pylint: disable=global-statement

    watcher_name = config.CONFIG["Server.master_watcher_class"]
    watcher_cls = DefaultMasterWatcher.classes[watcher_name]

    MASTER_WATCHER = watcher_cls()
