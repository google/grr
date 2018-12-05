#!/usr/bin/env python
"""Execute a Chipsec plugin on the client."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import logging
from logging import handlers
import os
import platform


from builtins import range  # pylint: disable=redefined-builtin

# pylint: disable=g-bad-import-order, g-import-not-at-top
# Import Chipsec configuration first so we can hook onto its internal path
# resolution.
from chipsec import file as chipsec_file

chipsec_file.main_is_frozen = lambda: False


# Initialize the Chipsec plugins
from chipsec import chipset
from chipsec import logger
from chipsec.hal import acpi
from chipsec.hal import spi
from chipsec.helper import oshelper

from grr_response_core import config
from grr_response_client import actions
from grr_response_client.client_actions import tempfiles
from grr_response_core.lib.rdfvalues import chipsec_types as rdf_chipsec_types

# pylint: enable=g-bad-import-order, g-import-not-at-top


class DumpFlashImage(actions.ActionPlugin):
  """A client action to collect the BIOS via SPI using Chipsec."""

  in_rdfvalue = rdf_chipsec_types.DumpFlashImageRequest
  out_rdfvalues = [rdf_chipsec_types.DumpFlashImageResponse]

  def LogError(self, err):
    self.logs.append("Error dumping Flash image.")
    self.logs.append("%r: %s" % (err, err))
    self.logs.extend(self.chipsec_log.getvalue().splitlines())
    self.SendReply(rdf_chipsec_types.DumpFlashImageResponse(logs=self.logs))

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
      syslog.info("%s: Runnning DumpFlashImage", config.CONFIG["Client.name"])

    self.logs = []
    self.chipsec_log = io.StringIO()

    if args.log_level:
      logger.logger().UTIL_TRACE = True
      if args.log_level == 2:
        logger.logger().VERBOSE = True
      logger.logger().logfile = self.chipsec_log
      logger.logger().LOG_TO_FILE = True

    # Create a temporary file to store the flash image.
    dest_fd, dest_pathspec = tempfiles.CreateGRRTempFileVFS(suffix=".flash")

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
        dest_fd.write(b"".join(bios))

    except (chipset.UnknownChipsetError, oshelper.OsHelperError) as err:
      # If the chipset is not recognised or if the helper threw an error,
      # report gracefully the error to the flow.
      if args.log_level:
        self.LogError(err)
      tempfiles.DeleteGRRTempFile(dest_pathspec.path)
      self.SendReply(
          rdf_chipsec_types.DumpFlashImageResponse(logs=["%s" % err],))
      return
    except Exception as err:  # pylint: disable=broad-except
      # In case an exception is raised, if the verbose mode
      # is enabled, return the raw logs from Chipsec.
      if args.log_level:
        self.LogError(err)
      tempfiles.DeleteGRRTempFile(dest_pathspec.path)
      raise

    if args.log_level:
      self.logs.extend(self.chipsec_log.getvalue().splitlines())

    if args.notify_syslog:
      syslog.info("%s: DumpFlashImage has completed successfully",
                  config.CONFIG["Client.name"])

    self.SendReply(
        rdf_chipsec_types.DumpFlashImageResponse(
            path=dest_pathspec, logs=self.logs))


class DumpACPITable(actions.ActionPlugin):
  """A client action to collect the ACPI table(s)."""

  in_rdfvalue = rdf_chipsec_types.DumpACPITableRequest
  out_rdfvalues = [rdf_chipsec_types.DumpACPITableResponse]

  def LogError(self, err):
    self.logs.append("Error dumping ACPI table.")
    self.logs.append("%r: %s" % (err, err))
    self.logs.extend(self.chipsec_log.getvalue().splitlines())
    self.SendReply(rdf_chipsec_types.DumpACPITableResponse(logs=self.logs))

  def Run(self, args):
    self.logs = []
    self.chipsec_log = io.StringIO()

    if args.logging:
      self.logs.append("Dumping %s" % args.table_signature)

      logger.logger().logfile = self.chipsec_log
      logger.logger().LOG_TO_FILE = True

    # Wrap most of Chipsec code to gather its logs in case of failure.
    try:
      # Initialise Chipsec (die early if unknown chipset)
      c = chipset.cs()
      # Platform = None, Start Driver = False
      c.init(None, False)
      a = acpi.ACPI(c)

      acpi_tables_raw = a.get_ACPI_table(args.table_signature)
      acpi_tables = []

      for i, table_address in enumerate(a.tableList[args.table_signature]):
        table_header, table_content = acpi_tables_raw[i]
        table_blob = table_header + table_content

        acpi_tables.append(
            rdf_chipsec_types.ACPITableData(
                table_address=table_address, table_blob=table_blob))
    except (chipset.UnknownChipsetError, OSError) as err:
      # Expected errors that might happen on the client
      # If the chipset is unknown or we encountered an error due to reading
      # an area we do not have access to using /dev/mem, simply return an
      # error message.
      if args.logging:
        self.LogError(err)
      self.SendReply(
          rdf_chipsec_types.DumpACPITableResponse(logs=["%s" % err],))
      return
    except Exception as err:  # pylint: disable=broad-except
      # In case an exception is raised, if the verbose mode
      # is enabled, return the raw logs from Chipsec.
      if args.logging:
        self.LogError(err)
      raise

    if not acpi_tables:
      self.logs.append(
          "No ACPI table with signature %s." % args.table_signature)
    else:
      self.logs.append(
          "ACPI table with signature %s has been successfully dumped." %
          args.table_signature)

    if args.logging:
      self.logs.extend(self.chipsec_log.getvalue().splitlines())

    self.SendReply(
        rdf_chipsec_types.DumpACPITableResponse(
            acpi_tables=acpi_tables, logs=self.logs))
