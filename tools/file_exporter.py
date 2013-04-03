#!/usr/bin/env python
"""Util for exporting files from the aff4 datastore."""



import sys


from grr.client import conf
from grr.client import conf as flags

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import aff4
from grr.lib import export_utils
from grr.lib import registry


flags.DEFINE_string("collection", None,
                    "AFF4 path to a collection to download/sync.")

flags.DEFINE_string("file", None,
                    "AFF4 path to download.")

flags.DEFINE_string("directory", None,
                    "AFF4 directory to download recursively.")

flags.DEFINE_integer("depth", 5,
                     "Depth for recursion on directory. Use 1 for just the "
                     "directory itself.")

flags.DEFINE_boolean("overwrite", False,
                     "If true, overwrite files if they exist.")

flags.DEFINE_string("output", None,
                    "Path to dump the data to.")

flags.DEFINE_boolean("export_client_data", True,
                     "Export a yaml file containing client data in the root "
                     "directory of the client output dir for collections. This "
                     "is useful for identifying the client that the files "
                     "belong to.")

flags.DEFINE_integer("threads", 10,
                     "Number of threads to use for export.")

FLAGS = flags.FLAGS


def Usage():
  print "Needs --collection or --file and --output args."
  print "e.g. --collection=aff4:/hunts/W:123456/Results --output=/tmp/foo"


def main(unused_argv):
  """Main."""
  if not FLAGS.output or not (FLAGS.collection or FLAGS.file or
                              FLAGS.directory):
    Usage()
    sys.exit(1)

  registry.Init()
  if FLAGS.collection:
    export_utils.DownloadCollection(FLAGS.collection, FLAGS.output,
                                    overwrite=FLAGS.overwrite,
                                    max_threads=FLAGS.threads,
                                    dump_client_info=FLAGS.export_client_data)
  elif FLAGS.file:
    export_utils.CopyAFF4ToLocal(FLAGS.file, FLAGS.output,
                                 overwrite=FLAGS.overwrite)

  elif FLAGS.directory:
    directory = aff4.FACTORY.Open(FLAGS.directory)
    export_utils.RecursiveDownload(directory, FLAGS.output,
                                   overwrite=FLAGS.overwrite, depth=FLAGS.depth)


def ConsoleMain():
  """Helper function for calling with setup tools entry points."""
  conf.StartMain(main)

if __name__ == "__main__":
  ConsoleMain()
