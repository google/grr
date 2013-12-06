#!/usr/bin/env python
"""'collection' plugin for GRR export tool."""



from grr.lib import aff4
from grr.lib import rdfvalue
from grr.tools.export_plugins import plugin


class CollectionExportPlugin(plugin.HuntOutputExportPlugin):
  """ExportPlugin that exports RDFValueCollections."""

  name = "collection"
  description = "Exports RDFValueCollection from AFF4."

  def ConfigureArgParser(self, parser):
    """Configure args parser for CollectionExportPlugin."""

    parser.add_argument("--path", type=rdfvalue.RDFURN, required=True,
                        help="AFF4 path to the collection to export.")

    parser.add_argument("--threads", type=int, default=8,
                        help="Maximum number of threads to use.")

    parser.add_argument("--batch", type=int, default=1000,
                        help="Size of batches processed by each thread.")

    parser.add_argument("--checkpoint_every", type=int, default=1000*1000,
                        help="Flush the results every time after processing "
                        "this number of values.")

    super(CollectionExportPlugin, self,).ConfigureArgParser(parser)

  def GetValuesSourceURN(self, args):
    return args.path

  def GetValuesForExport(self, args):
    return aff4.FACTORY.Open(args.path, mode="r",
                             aff4_type="RDFValueCollection")
