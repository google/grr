#!/usr/bin/env python
"""Util for exporting files from the aff4 datastore."""



import sys


# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import export_utils
from grr.lib import flags
from grr.lib import startup


flags.DEFINE_string("collection", None,
                    "AFF4 path to a collection to download/sync.")

flags.DEFINE_string("file", None,
                    "AFF4 path to download.")

flags.DEFINE_string("directory", None,
                    "AFF4 directory to download recursively.")

flags.DEFINE_integer("depth", 5,
                     "Depth for recursion on directory. Use 1 for just the "
                     "directory itself.")

flags.DEFINE_bool("overwrite", False,
                  "If true, overwrite files if they exist.")

flags.DEFINE_string("output", None,
                    "Path to dump the data to.")

flags.DEFINE_bool("export_client_data", True,
                  "Export a yaml file containing client data in the root "
                  "directory of the client output dir for collections. This "
                  "is useful for identifying the client that the files "
                  "belong to.")

flags.DEFINE_integer("threads", 10,
                     "Number of threads to use for export.")


def Usage():
  print "Needs --output and one of --collection --directory or --file."
  print "e.g. --collection=aff4:/hunts/W:123456/Results --output=/tmp/foo"


def main(unused_argv):
  """Main."""
  config_lib.CONFIG.AddContext(
      "Commandline Context",
      "Context applied for all command line tools")
  startup.Init()

  if not flags.FLAGS.output or not (flags.FLAGS.collection or flags.FLAGS.file
                                    or flags.FLAGS.directory):
    Usage()
    sys.exit(1)

  if flags.FLAGS.collection:
    export_utils.DownloadCollection(flags.FLAGS.collection, flags.FLAGS.output,
                                    overwrite=flags.FLAGS.overwrite,
                                    max_threads=flags.FLAGS.threads,
                                    dump_client_info=
                                    flags.FLAGS.export_client_data)
  elif flags.FLAGS.file:
    export_utils.CopyAFF4ToLocal(flags.FLAGS.file, flags.FLAGS.output,
                                 overwrite=flags.FLAGS.overwrite)

  elif flags.FLAGS.directory:
    directory = aff4.FACTORY.Open(flags.FLAGS.directory)
    if not list(directory.ListChildren()):
      print "%s contains no children." % directory.urn
      sys.exit(1)

    export_utils.RecursiveDownload(directory, flags.FLAGS.output,
                                   overwrite=flags.FLAGS.overwrite,
                                   depth=flags.FLAGS.depth)


def ConsoleMain():
  """Helper function for calling with setup tools entry points."""
  flags.StartMain(main)

if __name__ == "__main__":
  ConsoleMain()
