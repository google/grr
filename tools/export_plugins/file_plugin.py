#!/usr/bin/env python
"""'file' plugin for GRR export tool."""



from grr.lib import aff4
from grr.lib import data_store
from grr.lib import export_utils
from grr.tools.export_plugins import plugin


class FileExportPlugin(plugin.ExportPlugin):
  """ExportPlugin that downloads files and directories."""

  name = "file"
  description = "Downloads files/directories from AFF4."

  def ConfigureArgParser(self, parser):
    """Configures args parser for FileExportPlugin."""
    parser.add_argument("--path", required=True,
                        help="Path to the AFF4 object to download. "
                        "Can be either a file or a directory.")

    parser.add_argument("--output", required=True,
                        help="Directory downloaded files will be written to.")

    parser.add_argument("--depth", type=int, default=5,
                        help="Depth of recursion when path is a directory.")

    parser.add_argument("--overwrite", default=False,
                        help="If true, overwrite files if they exist.")

    parser.add_argument("--threads", type=int, default=8,
                        help="Maximum number of threads to use.")

  def Run(self, args):
    """Downloads files/directories with the given path."""

    try:
      directory = aff4.FACTORY.Open(args.path, "VFSDirectory",
                                    token=data_store.default_token)
    except aff4.InstantiationError:
      directory = None

    if directory:
      export_utils.RecursiveDownload(directory, args.output,
                                     overwrite=args.overwrite,
                                     max_depth=args.depth,
                                     max_threads=args.threads)
    else:
      export_utils.CopyAFF4ToLocal(args.path, args.output,
                                   overwrite=args.overwrite,
                                   token=data_store.default_token)
