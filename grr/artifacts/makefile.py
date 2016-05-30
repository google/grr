#!/usr/bin/env python
"""Update the artifacts directory from upstream."""
import fnmatch
import glob
import os
import StringIO
import urllib2
import zipfile


def main():
  data = urllib2.urlopen(
      "https://github.com/ForensicArtifacts/artifacts/archive/master.zip").read(
      )

  zip_obj = zipfile.ZipFile(StringIO.StringIO(data))
  # Remove all existing yaml files.
  for filename in glob.glob("*.yaml"):
    os.unlink(filename)

  for name in zip_obj.namelist():
    if fnmatch.fnmatch(name, "*/definitions/*.yaml"):
      print "Extracting %s" % name
      with open(os.path.basename(name), "wb") as fd:
        fd.write(zip_obj.open(name).read())


if __name__ == "__main__":
  main()
