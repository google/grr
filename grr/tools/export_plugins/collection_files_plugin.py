#!/usr/bin/env python
"""'collection_files' plugin for GRR export tool."""



from grr.lib import export_utils
from grr.tools.export_plugins import plugin


class CollectionFilesExportPlugin(plugin.ExportPlugin):
  """ExportPlugin that downloads files and directories."""

  name = "collection_files"
  description = "Downloads files referenced from the RDFValueCollection."

  def ConfigureArgParser(self, parser):
    """Configures args parser for CollectionFilesExportPlugin."""
    parser.add_argument("--path",
                        required=True,
                        help="Path to the RDFValueCollection. Files referenced "
                        "in this collection will be downloaded.")

    parser.add_argument("--output",
                        required=True,
                        help="Directory downloaded files will be written to.")

    parser.add_argument("--dump_client_info",
                        action="store_true",
                        default=False,
                        help="Detect client paths and dump a yaml version of "
                        "the client object to the root path. This is useful "
                        "for seeing the hostname/users of the "
                        "machine the client id refers to.")

    parser.add_argument("--flatten",
                        action="store_true",
                        default=False,
                        help="Create a 'files' folder in the output folder "
                        "with flat list of symlinks pointing to all the "
                        "found files.")

    parser.add_argument("--overwrite",
                        action="store_true",
                        default=False,
                        help="Overwrite files if they exist.")

    parser.add_argument("--threads",
                        type=int,
                        default=8,
                        help="Maximum number of threads to use.")

  def Run(self, args):
    """Downloads files referenced in the collection."""
    export_utils.DownloadCollection(args.path,
                                    args.output,
                                    overwrite=args.overwrite,
                                    dump_client_info=args.dump_client_info,
                                    flatten=args.flatten,
                                    max_threads=args.threads)
