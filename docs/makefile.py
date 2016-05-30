#!/usr/bin/env python
"""Update the local documentation from upstream."""
import os
import StringIO
import subprocess
import urllib2
import zipfile


def main():
  data = urllib2.urlopen(
      "https://github.com/google/grr-doc/archive/master.zip").read()

  zip_obj = zipfile.ZipFile(StringIO.StringIO(data))
  for name in zip_obj.namelist():
    if (os.path.basename(name) == "Makefile" or
        os.path.splitext(name)[1] in [".adoc", ".jpg", ".png"]):
      print "Extracting %s" % name
      out_filename = name.replace("grr-doc-master", ".")
      try:
        os.makedirs(os.path.dirname(out_filename))
      except OSError:
        pass
      with open(out_filename, "wb") as fd:
        fd.write(zip_obj.open(name).read())

  print "Generating html."
  subprocess.check_call(["make"], shell=True)


if __name__ == "__main__":
  main()
