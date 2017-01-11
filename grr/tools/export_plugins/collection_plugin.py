#!/usr/bin/env python
"""'collection' plugin for GRR export tool."""



from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.tools.export_plugins import plugin


class CollectionExportPlugin(plugin.OutputPluginBasedExportPlugin):
  """ExportPlugin that exports RDFValueCollections."""

  name = "collection"
  description = "Exports RDFValueCollection from AFF4."
  export_types = ["HuntResultCollection", "RDFValueCollection"]

  def ConfigureArgParser(self, parser):
    """Configure args parser for CollectionExportPlugin."""

    parser.add_argument(
        "--path",
        type=rdfvalue.RDFURN,
        required=True,
        help="AFF4 path to the collection to export.")

    parser.add_argument(
        "--threads",
        type=int,
        default=8,
        help="Maximum number of threads to use.")

    parser.add_argument(
        "--batch",
        type=int,
        default=1000,
        help="Size of batches processed by each thread.")

    parser.add_argument(
        "--checkpoint_every",
        type=int,
        default=1000 * 1000,
        help="Flush the results every time after processing "
        "this number of values.")

    parser.add_argument(
        "--no_legacy_warning_pause",
        action="store_true",
        default=False,
        help="Don't pause on legacy warning.")

    super(
        CollectionExportPlugin,
        self,).ConfigureArgParser(parser)

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

  def Run(self, args):
    base_url = config_lib.CONFIG.Get("AdminUI.url", context=["AdminUI Context"])

    source_path = rdfvalue.RDFURN(args.path)
    components = source_path.Split()
    if len(components) >= 2 and components[0] == "hunts":
      url = "%s/#/hunts/%s/results" % (base_url, components[1])
    elif len(components) >= 3:
      url = "%s/#/clients/%s/flows/%s/results" % (base_url, components[0],
                                                  components[2])
    else:
      url = "[AdminUI url unknown]"

    print "============================================================="
    print("WARNING: Command line export tool is DEPRECATED and will be "
          "removed soon.")
    print
    print "Please use the 'Download as' buttons on the results page instead."
    print "(the data in the selected format will be generated instantly):"
    print url
    print
    print "============================================================="
    print
    if not args.no_legacy_warning_pause:
      raw_input("Press Enter if you still want to continue...")

    super(CollectionExportPlugin, self).Run(args)
