#!/usr/bin/env python
"""'hash_file_store' plugin for GRR export tool."""



from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib.aff4_objects import filestore
from grr.tools.export_plugins import plugin


class HashFileStoreExportPlugin(plugin.OutputPluginBasedExportPlugin):
  """Exports hashes from HashFileStore via given hunt output plugin."""

  name = "hash_file_store"
  description = "Exports HashFileStore contents."

  def ConfigureArgParser(self, parser):
    """Configures args parser for HshFileStoreExportPlugin."""

    parser.add_argument("--threads",
                        type=int,
                        default=8,
                        help="Maximum number of threads to use.")

    parser.add_argument("--batch",
                        type=int,
                        default=1000,
                        help="Size of batches processed by each thread.")

    parser.add_argument("--checkpoint_every",
                        type=int,
                        default=1000 * 1000,
                        help="Flush the results every time after processing "
                        "this number of values.")

    super(HashFileStoreExportPlugin, self,).ConfigureArgParser(parser)

  def GetValuesSourceURN(self, unused_args):
    return rdfvalue.RDFURN("aff4:/files/hash")

  def GetValuesForExport(self, unused_args):
    return filestore.HashFileStore.ListHashes(token=data_store.default_token)
