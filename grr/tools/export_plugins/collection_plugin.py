#!/usr/bin/env python
"""'collection' plugin for GRR export tool."""



from grr.lib import aff4
from grr.lib import rdfvalue
from grr.tools.export_plugins import plugin


class CollectionExportPlugin(plugin.OutputPluginBasedExportPlugin):
  """ExportPlugin that exports RDFValueCollections."""

  name = "collection"
  description = "Exports RDFValueCollection from AFF4."
  export_types = ["HuntResultCollection", "RDFValueCollection"]

  def ConfigureArgParser(self, parser):
    """Configure args parser for CollectionExportPlugin."""

    parser.add_argument("--path",
                        type=rdfvalue.RDFURN,
                        required=True,
                        help="AFF4 path to the collection to export.")

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

    super(CollectionExportPlugin, self,).ConfigureArgParser(parser)

  def GetValuesSourceURN(self, args):
    return args.path

  def GetValuesForExport(self, args):
    collection = aff4.FACTORY.Open(args.path, mode="r")
    for aff4_type in self.export_types:
      if isinstance(collection, aff4.AFF4Object.classes[aff4_type]):
        break
    else:
      raise aff4.InstantiationError(
          "Object %s is of type %s, but required_type is one of %s" %
          (collection, collection.__class__.__name__, self.export_types))
    return collection
