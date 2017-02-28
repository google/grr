#!/usr/bin/env python
"""'collection' plugin for GRR export tool."""



from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib.hunts import results
from grr.tools.export_plugins import plugin


class CollectionExportPlugin(plugin.OutputPluginBasedExportPlugin):
  """ExportPlugin that exports hunt results collections."""

  name = "collection"
  description = "Exports hunt results collections from AFF4."
  export_types = ["HuntResultCollection"]

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
    return results.HuntResultCollection(
        args.path, token=data_store.default_token)

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
