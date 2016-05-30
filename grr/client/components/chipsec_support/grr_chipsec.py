#!/usr/bin/env python
"""Execute a Chipsec plugin on the client."""

__author__ = "tweksteen@gmail.com (Thiebaud Weksteen)"

import logging
from logging import handlers

from grr.client import actions
from grr.client.client_actions import tempfiles
from grr.lib import config_lib

# pylint: disable=g-import-not-at-top
# When deployed as a component, import the dependency directly
# Otherwise (unittest), load according to the grr package
try:
  import chipsec_types
except ImportError:
  from grr.client.components.chipsec_support import chipsec_types

# This file is included when running the test case.
try:
  # Initialize the Chipsec plugins, so pylint: disable=unused-import
  from chipsec import chipset
  from chipsec.hal import spi
  from chipsec.logger import logger
  # pylint: enable=unused-import
except ImportError:
  pass
# pylint: enable=g-import-not-at-top


class DumpFlashImage(actions.ActionPlugin):
  """A client action to collect the BIOS via SPI using Chipsec."""

  in_rdfvalue = chipsec_types.DumpFlashImageRequest
  out_rdfvalues = [chipsec_types.DumpFlashImageResponse]

  def ReadAndDeleteChipsecLogs(self):
    logger().close()
    with open(self.log_pathspec.path) as log_f:
      logs = log_f.read().splitlines()
    tempfiles.DeleteGRRTempFile(self.log_pathspec.path)
    return logs

  def Run(self, args):
    # Due to talking raw to hardware, this action has some inevitable risk of
    # crashing the machine, so we need to flush the transaction log to ensure
    # we know when this happens.
    self.SyncTransactionLog()

    # Temporary extra logging for Ubuntu
    # TODO(user): Add generic hunt flag to notify syslog before running each
    # client action.
    if args.notify_syslog:
      syslog = logging.getLogger("chipsec_grr")
      syslog.setLevel(logging.INFO)
      syslog.addHandler(handlers.SysLogHandler(address="/dev/log"))
      syslog.info("%s: Runnning DumpFlashImage",
                  config_lib.CONFIG["Client.name"])

    logs = []

    if args.log_level:
      # Create a temporary file to store the log output as
      # Chipsec does not support in-memory logging.
      _, self.log_pathspec = tempfiles.CreateGRRTempFileVFS()
      logger().UTIL_TRACE = True
      if args.log_level == 2:
        logger().VERBOSE = True
      logger().set_log_file(self.log_pathspec.path)

    # Create a temporary file to store the flash image.
    dest_fd, dest_pathspec = tempfiles.CreateGRRTempFileVFS()

    # Wrap most of Chipsec code to gather its logs in case of failure.
    try:
      # Initialise Chipsec (die early if unknown chipset)
      c = chipset.cs()
      # Platform = None, Start Driver = False
      c.init(None, False)
      s = spi.SPI(c)

      # Use hal.spi from chipsec to write BIOS to that file.
      with dest_fd:
        # Based on Chipsec code, rely on the address of BIOS(=1) region to
        # determine the size of the flash.
        _, limit, _ = s.get_SPI_region(1)
        spi_size = limit + 1
        # Read args.chunk_size bytes at a time and heartbeat.
        bios = []
        for i in range(0, spi_size, args.chunk_size):
          bios.extend(s.read_spi(i, args.chunk_size))
          self.Progress()
        dest_fd.write("".join(bios))

    except Exception as err:  # pylint: disable=broad-except
      # In case an exception is raised, if the verbose mode
      # is enabled, return the raw logs from Chipsec.
      if args.log_level:
        logs = self.ReadAndDeleteChipsecLogs()
        logs.append("%r: %s" % (err, err))
        self.SendReply(chipsec_types.DumpFlashImageResponse(logs=logs))
        tempfiles.DeleteGRRTempFile(dest_pathspec.path)
      if isinstance(err, chipset.UnknownChipsetError):
        # If the chipset is unknown, simply returns an error message
        self.SendReply(chipsec_types.DumpFlashImageResponse(logs=["%s" % err],))
        return
      raise

    if args.log_level:
      logs = self.ReadAndDeleteChipsecLogs()

    if args.notify_syslog:
      syslog.info("%s: DumpFlashImage has completed successfully",
                  config_lib.CONFIG["Client.name"])

    self.SendReply(chipsec_types.DumpFlashImageResponse(path=dest_pathspec,
                                                        logs=logs))
