#!/usr/bin/env python
"""Script for importing NSRL files."""


import csv
import os

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flags
from grr.lib import startup
from grr.lib import utils

from grr.lib.aff4_objects import filestore


flags.DEFINE_string("filename", "", "File with hashes.")
flags.DEFINE_integer("start", None, "Start row in the file.")


def _ImportRow(store, row, product_code_list, op_system_code_list):
  sha1 = row[0].lower()
  md5 = row[1].lower()
  crc = int(row[2].lower(), 16)
  file_name = utils.SmartUnicode(row[3])
  file_size = int(row[4])
  special_code = row[7]
  store.AddHash(sha1, md5, crc, file_name, file_size,
                product_code_list, op_system_code_list, special_code)


def ImportFile(store, filename, start):
  """Import hashes from 'filename' into 'store'."""
  with open(filename, "rb") as fp:
    reader = csv.reader(fp, delimiter=",", quotechar="\"")
    i = 0
    current_row = None
    product_code_list = []
    op_system_code_list = []
    for row in reader:
      # Skip first row.
      i += 1
      if i and i % 5000 == 0:
        data_store.DB.Flush()
        print "Imported %d hashes" % i
      if i > 1:
        if len(row) != 8:
          continue
        try:
          if i < start:
            continue
          if current_row:
            if current_row[0] == row[0]:
              # Same hash, add product/system
              product_code_list.append(int(row[5]))
              op_system_code_list.append(row[6])
              continue
            # Fall through and add current row.
          else:
            # First row.
            current_row = row
            product_code_list = [int(row[5])]
            op_system_code_list = [row[6]]
            continue
          _ImportRow(store, current_row, product_code_list,
                     op_system_code_list)
          # Set new hash.
          current_row = row
          product_code_list = [int(row[5])]
          op_system_code_list = [row[6]]
        except Exception as e:  # pylint: disable=broad-except
          print "Failed at %d with %s" % (i, str(e))
          return i - 1
    if current_row:
      _ImportRow(store, current_row, product_code_list, op_system_code_list)
    return i


def main(unused_argv):
  """Main."""
  startup.Init()

  filename = flags.FLAGS.filename
  if not os.path.exists(filename):
    print "File %s does not exist" % filename
    return

  with aff4.FACTORY.Create(filestore.NSRLFileStore.PATH, "NSRLFileStore",
                           mode="rw", token=aff4.FACTORY.root_token) as store:
    imported = ImportFile(store, filename, flags.FLAGS.start)
    data_store.DB.Flush()
    print "Imported %d hashes" % imported

if __name__ == "__main__":
  flags.StartMain(main)
